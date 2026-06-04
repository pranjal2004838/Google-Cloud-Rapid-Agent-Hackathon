"""
RecordUpdateAgent — Single Verb: PERSISTS

Responsibilities:
- Inserts new patient record OR updates existing patient with new visit
- Builds audit event with hash-chain integrity
- Reports write result (record_id, visit_count, audit validity)

Hard Boundaries (what this agent must NOT do):
- Must NOT re-read or re-interpret prescription images
- Must NOT re-run safety checks or evaluate risks
- Must NOT modify extraction data or patient context
- Must NOT generate doctor-facing explanations
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from datetime import date, datetime

from agent.orchestration.state import WorkflowState, WriteResult
from agent.gcp.kms import encrypt_data
from agent.gcp.logger import get_logger
from agent.gcp.pubsub import publish_alert

logger = get_logger(__name__)


class RecordUpdateAgent:
    """
    Persists the final patient record.
    Accepts optional db_collection and in_memory_store for testability.
    """

    def __init__(self, db_collection=None, in_memory_store: list | None = None):
        """
        Args:
            db_collection: A pymongo Collection or None.
            in_memory_store: A list used as fallback store.
        """
        self._collection = db_collection
        self._memory = in_memory_store if in_memory_store is not None else []

    async def run(self, state: WorkflowState) -> WorkflowState:
        """
        Execute record persistence and write ONLY to state.write_result.
        Requires state.request, state.extracted_data, and state.patient_context.
        """
        extracted = state.extracted_data
        context = state.patient_context
        request = state.request

        if extracted is None or context is None:
            state.write_result = WriteResult(record_id="", is_returning=False)
            return state

        phone = request.phone
        doctor_name = extracted.doctor_name
        ip_address = request.ip_address

        # Build visit document
        visit = {
            "visit_id": str(uuid.uuid4()),
            "date": extracted.visit_date or str(date.today()),
            "created_at": self._utc_now_iso(),
            "doctor": doctor_name,
            "clinic": extracted.clinic_name,
            "diagnosis": extracted.diagnosis,
            "medicines": [m.model_dump() for m in extracted.medicines],
            "tests": extracted.tests_ordered,
            "notes": extracted.notes,
            "source_document": request.gcs_upload_result,
        }

        if context.patient_exists:
            result = await asyncio.to_thread(
                self._update_existing,
                phone,
                visit,
                context,
                extracted,
                doctor_name,
                ip_address,
            )
        else:
            result = await asyncio.to_thread(
                self._insert_new,
                phone,
                visit,
                context,
                extracted,
                doctor_name,
                ip_address,
            )

        state.write_result = result
        
        # Publish an audit trail event using Pub/Sub
        if result.record_id:
            publish_alert(
                alert_type="AUDIT_TRAIL_UPDATE",
                message=f"Patient record updated by {doctor_name} at {ip_address}",
                patient_id=result.record_id
            )
            
        return state

    # ─── Private: Update Existing Patient ─────────────────────────────────────

    def _update_existing(
        self, phone, visit, context, extracted, doctor_name, ip_address
    ) -> WriteResult:
        """Add new visit to existing patient, append audit event."""
        existing = self._find_patient(phone)
        if existing is None:
            return WriteResult(record_id="", is_returning=False)

        previous_hash = self._get_last_hash(existing)
        audit_event = self._build_audit_event(
            action="PRESCRIPTION_UPLOADED",
            doctor=doctor_name,
            ip_address=ip_address,
            details={
                "phone": phone,
                "visit_id": visit["visit_id"],
                "duplicate_check": context.duplicate_check,
            },
            previous_hash=previous_hash,
        )

        all_allergies = context.all_allergies

        if self._collection is not None:
            self._collection.update_one(
                {"_id": existing["_id"]},
                {
                    "$push": {"visits": visit, "audit_log": audit_event},
                    "$set": {"known_allergies": all_allergies},
                },
            )
            record_id = str(existing["_id"])
        else:
            existing["known_allergies"] = all_allergies
            existing["visits"].append(visit)
            existing.setdefault("audit_log", []).append(audit_event)
            record_id = existing.get("patient_id", "")

        visit_count = len(existing.get("visits", [])) + (1 if self._collection is not None else 0)
        audit_log = existing.get("audit_log", [])
        if self._collection is not None:
            audit_log = audit_log + [audit_event]

        return WriteResult(
            record_id=record_id,
            is_returning=True,
            visit_count=visit_count,
            audit_event=audit_event,
            audit_chain_valid=self._verify_chain(audit_log),
            audit_entries=len(audit_log),
        )

    # ─── Private: Insert New Patient ──────────────────────────────────────────

    def _insert_new(
        self, phone, visit, context, extracted, doctor_name, ip_address
    ) -> WriteResult:
        """Create a new patient document."""
        audit_event = self._build_audit_event(
            action="PRESCRIPTION_UPLOADED",
            doctor=doctor_name,
            ip_address=ip_address,
            details={"phone": phone, "visit_id": visit["visit_id"], "duplicate_check": {"is_duplicate": False}},
            previous_hash="",
        )

        # Encrypt sensitive PII using Cloud KMS
        encrypted_pii = encrypt_data({
            "name": extracted.patient_name,
            "age": extracted.patient_age,
            "gender": extracted.patient_gender
        })

        patient_doc = {
            "patient_id": str(uuid.uuid4()),
            "phone": phone,
            "name": "[ENCRYPTED_KMS]",
            "age": "[ENCRYPTED_KMS]",
            "gender": "[ENCRYPTED_KMS]",
            "secure_pii": encrypted_pii,
            "known_allergies": context.all_allergies,
            "conditions": extracted.diagnosis,
            "visits": [visit],
            "audit_log": [audit_event],
            "created_at": datetime.now().isoformat(),
        }

        if self._collection is not None:
            result = self._collection.insert_one(patient_doc)
            record_id = str(result.inserted_id)
        else:
            self._memory.append(patient_doc)
            record_id = patient_doc["patient_id"]

        return WriteResult(
            record_id=record_id,
            is_returning=False,
            visit_count=1,
            audit_event=audit_event,
            audit_chain_valid=True,
            audit_entries=1,
        )

    # ─── Private Helpers ──────────────────────────────────────────────────────

    def _find_patient(self, phone: str) -> dict | None:
        if not phone:
            return None
        if self._collection is not None:
            return self._collection.find_one({"phone": phone})
        return next((p for p in self._memory if p.get("phone") == phone), None)

    @staticmethod
    def _get_last_hash(patient: dict) -> str:
        audit_log = patient.get("audit_log", [])
        if audit_log:
            return audit_log[-1].get("hash", "")
        return ""

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    @staticmethod
    def _build_audit_event(action, doctor, ip_address, details, previous_hash) -> dict:
        timestamp = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        payload = {
            "timestamp": timestamp,
            "action": action,
            "doctor": doctor or "Unknown",
            "ip_address": ip_address or "unknown",
            "details": details or {},
        }
        serial = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        hash_val = hashlib.sha256(f"{previous_hash}|{serial}".encode("utf-8")).hexdigest()
        return {
            **payload,
            "previous_hash": previous_hash or "",
            "hash": hash_val,
        }

    @staticmethod
    def _verify_chain(audit_log: list) -> bool:
        """Verify hash-chain integrity."""
        previous_hash = ""
        for entry in audit_log:
            payload = {
                "timestamp": entry.get("timestamp"),
                "action": entry.get("action"),
                "doctor": entry.get("doctor"),
                "ip_address": entry.get("ip_address"),
                "details": entry.get("details", {}),
            }
            if entry.get("previous_hash", "") != previous_hash:
                return False
            serial = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            expected = hashlib.sha256(f"{previous_hash}|{serial}".encode("utf-8")).hexdigest()
            if entry.get("hash") != expected:
                return False
            previous_hash = entry.get("hash", "")
        return True
