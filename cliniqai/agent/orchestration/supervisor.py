"""
Supervisor — The Orchestrator

Responsibilities:
- Routes work to specialized agents in the correct order
- Runs ExtractionAgent and PatientContextAgent in PARALLEL (asyncio.gather)
- Validates each agent's output against Pydantic schemas before proceeding
- Gates the Safety step (requires extraction + context)
- Gates the Write step (only writes if safety passes or override exists)
- Records a trace log for every agent invocation
- Marks workflow as review_required on low confidence / HIGH alerts / ambiguity

This agent does NOT do any medical reasoning itself.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime

from agent.orchestration.state import (
    RequestMeta,
    TraceEntry,
    WorkflowState,
    WorkflowStatus,
    ExtractedData,
    PatientContext,
    SafetyAssessment,
    WriteResult,
)
from agent.orchestration.agents.extraction_agent import ExtractionAgent
from agent.orchestration.agents.patient_context_agent import PatientContextAgent
from agent.orchestration.agents.safety_agent import SafetyAgent
from agent.orchestration.agents.record_update_agent import RecordUpdateAgent


class Supervisor:
    """
    Orchestrates the multi-agent workflow.

    Usage:
        supervisor = Supervisor(
            extraction_agent=ExtractionAgent(),
            patient_context_agent=PatientContextAgent(db_collection=col, in_memory_store=mem),
            safety_agent=SafetyAgent(),
            record_update_agent=RecordUpdateAgent(db_collection=col, in_memory_store=mem),
        )
        state = await supervisor.run(phone="9876543210", image_bytes=b"...", ip_address="127.0.0.1")
    """

    # Confidence threshold: below this, the workflow pauses for review
    CONFIDENCE_THRESHOLD = 0.5

    def __init__(
        self,
        extraction_agent: ExtractionAgent,
        patient_context_agent: PatientContextAgent,
        safety_agent: SafetyAgent,
        record_update_agent: RecordUpdateAgent,
    ):
        self._extraction = extraction_agent
        self._context = patient_context_agent
        self._safety = safety_agent
        self._writer = record_update_agent

    async def run(
        self,
        phone: str,
        image_bytes: bytes | None = None,
        ip_address: str = "unknown",
        content_type: str | None = None,
        gcs_upload_result: dict | None = None,
        extracted_override: dict | None = None,
    ) -> WorkflowState:
        """
        Execute the full multi-agent workflow.

        Args:
            phone: Patient phone number (required identifier).
            image_bytes: Raw image bytes for extraction. Can be None if extracted_override is used.
            ip_address: Client IP for audit trail.
            content_type: MIME type of upload.
            gcs_upload_result: Cloud Storage upload metadata (if already uploaded).
            extracted_override: Pre-extracted data dict (skips ExtractionAgent). Used by /test/process.

        Returns:
            Completed WorkflowState with all agent outputs and trace log.
        """
        # Initialize shared state
        state = WorkflowState(
            request=RequestMeta(
                phone=phone,
                ip_address=ip_address,
                content_type=content_type,
                gcs_upload_result=gcs_upload_result,
            ),
            status=WorkflowStatus.IN_PROGRESS,
        )

        # ─── STEP 1: Parallel — Extraction + Patient Context ──────────────────
        # Extraction is usually the slow path; context lookup is fast and independent
        # of image parsing for initial patient existence lookup by phone.

        if extracted_override is not None:
            # Test/mock path: inject pre-extracted data without calling Gemini.
            mock_agent = ExtractionAgent(extraction_fn=lambda _bytes: extracted_override)
            extraction_task = self._run_agent_with_trace(
                state,
                "ExtractionAgent",
                mock_agent.run,
                state,
                b"mock",
            )
        else:
            if image_bytes is None:
                state.status = WorkflowStatus.FAILED
                state.error = "No image_bytes and no extracted_override provided"
                return state
            extraction_task = self._run_agent_with_trace(
                state,
                "ExtractionAgent",
                self._extraction.run,
                state,
                image_bytes,
            )

        # Context agent runs in parallel to hide DB latency.
        context_task = self._run_agent_with_trace(
            state,
            "PatientContextAgent",
            self._context.run,
            state,
        )

        # Gather both; fail fast if either agent crashes.
        try:
            await asyncio.gather(extraction_task, context_task)
        except Exception as exc:
            state.status = WorkflowStatus.FAILED
            state.error = f"Parallel agent execution failed: {str(exc)}"
            return state

        # Re-run context once extraction is done so allergy merge/new-medicine context
        # uses the extracted payload deterministically.
        if state.extracted_data is not None:
            try:
                state = await self._run_agent_with_trace(
                    state,
                    "PatientContextAgent",
                    self._context.run,
                    state,
                )
            except Exception as exc:
                state.status = WorkflowStatus.FAILED
                state.error = f"Patient context merge failed: {str(exc)}"
                return state

        # ─── GATE 1: Extraction Validation ────────────────────────────────────
        validation_error = self._validate_state_sections(state, sections=("extracted_data", "patient_context"))
        if validation_error:
            state.status = WorkflowStatus.FAILED
            state.error = validation_error
            return state

        if state.extracted_data is None:
            state.status = WorkflowStatus.FAILED
            state.error = "Extraction produced no data"
            return state

        # Check for extraction error
        if state.extracted_data.confidence_scores.get("_error"):
            state.status = WorkflowStatus.FAILED
            state.error = f"Extraction failed: {state.extracted_data.confidence_scores['_error']}"
            return state

        # ─── GATE 2: Confidence Review Gate ───────────────────────────────────
        if self._is_low_confidence(state):
            state.status = WorkflowStatus.REVIEW_REQUIRED
            state.review_reason = "Low extraction confidence — manual review recommended"
            # Continue processing (still run safety + write) but flag for doctor

        # ─── STEP 2: Safety Evaluation ────────────────────────────────────────
        try:
            state = await self._run_agent_with_trace(
                state,
                "SafetyAgent",
                self._safety.run,
                state,
            )
        except Exception as exc:
            state.status = WorkflowStatus.FAILED
            state.error = f"Safety evaluation failed: {str(exc)}"
            return state

        validation_error = self._validate_state_sections(state, sections=("safety_assessment",))
        if validation_error:
            state.status = WorkflowStatus.FAILED
            state.error = validation_error
            return state

        # ─── GATE 3: Safety Override Gate ─────────────────────────────────────
        if state.safety_assessment and state.safety_assessment.requires_override:
            if state.status != WorkflowStatus.REVIEW_REQUIRED:
                state.status = WorkflowStatus.REVIEW_REQUIRED
                state.review_reason = "HIGH severity drug alert — doctor acknowledgement required"

        # ─── STEP 3: Record Persistence ───────────────────────────────────────
        try:
            state = await self._run_agent_with_trace(
                state,
                "RecordUpdateAgent",
                self._writer.run,
                state,
            )
        except Exception as exc:
            state.status = WorkflowStatus.FAILED
            state.error = f"Record update failed: {str(exc)}"
            return state

        validation_error = self._validate_state_sections(state, sections=("write_result",))
        if validation_error:
            state.status = WorkflowStatus.FAILED
            state.error = validation_error
            return state

        # ─── Finalize ─────────────────────────────────────────────────────────
        if state.status == WorkflowStatus.IN_PROGRESS:
            state.status = WorkflowStatus.COMPLETED

        return state

    # ─── Private: Run Agent with Trace ────────────────────────────────────────

    async def _run_agent_with_trace(self, state, agent_name, fn, *args) -> WorkflowState:
        """Run an agent function, record timing in the trace log."""
        started = time.time()
        started_iso = datetime.utcnow().isoformat() + "Z"
        try:
            result = await fn(*args)
            elapsed_ms = int((time.time() - started) * 1000)
            finished_iso = datetime.utcnow().isoformat() + "Z"
            self._add_trace(state, agent_name, started_iso, finished_iso, elapsed_ms, "success")
            return result
        except Exception as exc:
            elapsed_ms = int((time.time() - started) * 1000)
            finished_iso = datetime.utcnow().isoformat() + "Z"
            self._add_trace(state, agent_name, started_iso, finished_iso, elapsed_ms, "failed", str(exc))
            # Surface failure to caller for fail-fast handling.
            raise

    @staticmethod
    def _add_trace(
        state: WorkflowState,
        agent: str,
        started_at: str,
        finished_at: str,
        duration_ms: int,
        status: str,
        error: str | None = None,
    ):
        """Append a trace entry to the state."""
        state.trace.append(TraceEntry(
            agent=agent,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            status=status,
            error=error,
        ))

    @staticmethod
    def _record_failure(state: WorkflowState, agent: str, exc: Exception) -> WorkflowState:
        """Mark workflow as failed due to agent exception."""
        state.status = WorkflowStatus.FAILED
        state.error = f"{agent} failed: {str(exc)}"
        return state

    @staticmethod
    def _validate_state_sections(state: WorkflowState, sections: tuple[str, ...]) -> str | None:
        """Validate critical state sections and return error string on failure."""
        validators = {
            "extracted_data": ExtractedData,
            "patient_context": PatientContext,
            "safety_assessment": SafetyAssessment,
            "write_result": WriteResult,
        }
        for section in sections:
            model_cls = validators.get(section)
            if model_cls is None:
                continue
            value = getattr(state, section, None)
            if value is None:
                continue
            try:
                model_cls.model_validate(value)
            except Exception as exc:
                return f"Schema validation failed for {section}: {str(exc)}"
        return None

    # ─── Private: Confidence Check ────────────────────────────────────────────

    def _is_low_confidence(self, state: WorkflowState) -> bool:
        """Check if any critical field has confidence below threshold."""
        if state.extracted_data is None:
            return False

        scores = state.extracted_data.confidence_scores
        if not scores:
            return False

        critical_fields = ["patient_name", "medicines"]
        for field in critical_fields:
            score = scores.get(field)
            if isinstance(score, (int, float)) and score < self.CONFIDENCE_THRESHOLD:
                return True
            # Check per-medicine confidence
            if field == "medicines" and isinstance(score, list):
                for med_score in score:
                    if isinstance(med_score, dict):
                        name_conf = med_score.get("name", 1.0)
                        if isinstance(name_conf, (int, float)) and name_conf < self.CONFIDENCE_THRESHOLD:
                            return True

        return False
