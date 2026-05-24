"""
Shared Workflow State — the "Hospital Chart"

Every agent reads from and writes to this single state object.
Each agent is allowed to update ONLY its own section.
Pydantic enforces schema correctness at every handoff boundary.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# ─── Canonical Schemas (shared vocabulary) ────────────────────────────────────

class Medicine(BaseModel):
    """Canonical medicine representation used by ALL agents."""
    name: str
    dose: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    confidence: Optional[float] = None


class Alert(BaseModel):
    """Canonical alert representation used by ALL agents."""
    severity: str  # HIGH, MEDIUM, LOW
    type: str  # ALLERGY, INTERACTION, CROSS_REACTIVITY
    message: str
    evidence: Optional[str] = None
    requires_override: bool = False


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REVIEW_REQUIRED = "review_required"
    FAILED = "failed"


# ─── Agent-Owned State Sections ───────────────────────────────────────────────

class RequestMeta(BaseModel):
    """Immutable request context set once at workflow start."""
    phone: str
    ip_address: str = "unknown"
    content_type: Optional[str] = None
    gcs_uri: Optional[str] = None
    gcs_upload_result: Optional[dict] = None


class ExtractedData(BaseModel):
    """Output of ExtractionAgent. Never modified by other agents."""
    patient_name: str = "Unknown"
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None
    visit_date: Optional[str] = None
    doctor_name: Optional[str] = None
    clinic_name: Optional[str] = None
    diagnosis: list[str] = Field(default_factory=list)
    medicines: list[Medicine] = Field(default_factory=list)
    tests_ordered: list[str] = Field(default_factory=list)
    allergies_mentioned: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    confidence_scores: dict[str, Any] = Field(default_factory=dict)
    raw_extraction: Optional[dict] = None


class PatientContext(BaseModel):
    """Output of PatientContextAgent. Never modified by other agents."""
    patient_exists: bool = False
    patient_id: Optional[str] = None
    existing_allergies: list[str] = Field(default_factory=list)
    all_allergies: list[str] = Field(default_factory=list)
    current_medicines: list[Medicine] = Field(default_factory=list)
    visit_count: int = 0
    duplicate_check: dict = Field(default_factory=lambda: {"is_duplicate": False})


class SafetyAssessment(BaseModel):
    """Output of SafetyAgent. Never modified by other agents."""
    has_alerts: bool = False
    alert_count: int = 0
    high_severity_count: int = 0
    alerts: list[Alert] = Field(default_factory=list)
    requires_override: bool = False


class WriteResult(BaseModel):
    """Output of RecordUpdateAgent. Never modified by other agents."""
    record_id: str = ""
    is_returning: bool = False
    visit_count: int = 1
    audit_event: Optional[dict] = None
    audit_chain_valid: bool = True
    audit_entries: int = 0


# ─── Trace Entry (for debugging) ─────────────────────────────────────────────

class TraceEntry(BaseModel):
    """One step in the workflow trace. Written by Supervisor only."""
    agent: str
    started_at: str
    finished_at: str
    duration_ms: int
    status: str  # "success", "failed", "skipped"
    error: Optional[str] = None


# ─── The Complete Workflow State ──────────────────────────────────────────────

class WorkflowState(BaseModel):
    """
    The shared state object ("Hospital Chart") for the entire workflow.

    Rules:
    - ExtractionAgent writes ONLY to `extracted_data`
    - PatientContextAgent writes ONLY to `patient_context`
    - SafetyAgent writes ONLY to `safety_assessment`
    - RecordUpdateAgent writes ONLY to `write_result`
    - Supervisor writes to `status`, `trace`, and `review_reason`
    """
    # Request context (set once, immutable after)
    request: RequestMeta

    # Agent-owned sections (each filled by exactly one agent)
    extracted_data: Optional[ExtractedData] = None
    patient_context: Optional[PatientContext] = None
    safety_assessment: Optional[SafetyAssessment] = None
    write_result: Optional[WriteResult] = None

    # Workflow metadata (Supervisor-owned)
    status: WorkflowStatus = WorkflowStatus.PENDING
    review_reason: Optional[str] = None
    trace: list[TraceEntry] = Field(default_factory=list)
    error: Optional[str] = None
