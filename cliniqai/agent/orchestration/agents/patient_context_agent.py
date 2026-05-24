"""
PatientContextAgent — Single Verb: RETRIEVES

Responsibilities:
- Looks up patient by phone number (MongoDB or in-memory)
- Merges existing allergies with newly extracted allergies
- Collects current medicines from prior visits
- Detects duplicate visits (same meds within 7 days)

Hard Boundaries (what this agent must NOT do):
- Must NOT interpret or re-read the prescription image
- Must NOT evaluate drug safety or interactions
- Must NOT write/update any records (that is RecordUpdateAgent's job)
- Must NOT generate doctor-facing text
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from agent.orchestration.state import Medicine, PatientContext, WorkflowState


class PatientContextAgent:
    """
    Retrieves patient context from the data store.
    Accepts optional db_collection and in_memory_store for testability.
    """

    def __init__(self, db_collection=None, in_memory_store: list | None = None):
        """
        Args:
            db_collection: A pymongo Collection or None.
            in_memory_store: A list used as fallback store when Mongo is unavailable.
        """
        self._collection = db_collection
        self._memory = in_memory_store if in_memory_store is not None else []

    async def run(self, state: WorkflowState) -> WorkflowState:
        """
        Execute patient lookup and write ONLY to state.patient_context.
        Requires state.request.phone and state.extracted_data to be set.
        """
        phone = state.request.phone
        extracted = state.extracted_data

        # Fetch existing patient
        existing = await asyncio.to_thread(self._find_patient, phone)

        if existing is None:
            # New patient — minimal context
            new_allergies = extracted.allergies_mentioned if extracted else []
            state.patient_context = PatientContext(
                patient_exists=False,
                all_allergies=new_allergies,
                visit_count=0,
            )
            return state

        # Existing patient — build full context
        existing_allergies = existing.get("known_allergies", [])
        new_allergies = extracted.allergies_mentioned if extracted else []
        all_allergies = list(set(existing_allergies + new_allergies))

        # Gather current medicines from all prior visits
        current_meds: list[Medicine] = []
        for visit in existing.get("visits", []):
            for m in visit.get("medicines", []):
                current_meds.append(Medicine(
                    name=m.get("name", ""),
                    dose=m.get("dose"),
                    frequency=m.get("frequency"),
                    duration=m.get("duration"),
                ))

        # Duplicate visit detection
        new_medicines = extracted.medicines if extracted else []
        duplicate_check = self._find_duplicate_visit(
            existing.get("visits", []),
            new_medicines,
        )

        patient_id = str(existing.get("_id", existing.get("patient_id", "")))

        state.patient_context = PatientContext(
            patient_exists=True,
            patient_id=patient_id,
            existing_allergies=existing_allergies,
            all_allergies=all_allergies,
            current_medicines=current_meds,
            visit_count=len(existing.get("visits", [])),
            duplicate_check=duplicate_check,
        )
        return state

    # ─── Private Helpers ──────────────────────────────────────────────────────

    def _find_patient(self, phone: str) -> dict | None:
        """Look up patient by phone from Mongo or in-memory."""
        if not phone:
            return None

        if self._collection is not None:
            return self._collection.find_one({"phone": phone})

        # In-memory fallback
        return next((p for p in self._memory if p.get("phone") == phone), None)

    def _find_duplicate_visit(
        self,
        visits: list[dict],
        new_medicines: list[Medicine],
        threshold: float = 0.95,
    ) -> dict:
        """
        Detect likely duplicate visit from same meds within 7 days.
        Returns {"is_duplicate": False} or duplicate metadata.
        """
        if not new_medicines:
            return {"is_duplicate": False}

        now = datetime.utcnow()
        window_start = now - timedelta(days=7)
        new_names = {m.name.strip().lower() for m in new_medicines if m.name}
        best_match = None

        for visit in visits:
            visit_time = self._parse_visit_time(visit)
            if visit_time < window_start:
                continue

            existing_names = {
                (m.get("name") or "").strip().lower()
                for m in visit.get("medicines", [])
            }
            existing_names.discard("")

            if not existing_names and not new_names:
                similarity = 1.0
            elif not existing_names or not new_names:
                similarity = 0.0
            else:
                overlap = len(existing_names & new_names)
                similarity = overlap / max(len(existing_names), len(new_names))

            if similarity >= threshold:
                if best_match is None or similarity > best_match["similarity"]:
                    best_match = {
                        "visit": visit,
                        "similarity": similarity,
                        "visit_time": visit_time,
                    }

        if best_match is None:
            return {"is_duplicate": False}

        delta = now - best_match["visit_time"]
        hours = max(1, int(delta.total_seconds() // 3600))
        return {
            "is_duplicate": True,
            "previous_visit_id": best_match["visit"].get("visit_id", "unknown"),
            "time_diff": f"{hours} hour(s) ago",
            "similarity": round(best_match["similarity"], 3),
            "warning": "This looks like a duplicate prescription. Please verify before saving.",
        }

    @staticmethod
    def _parse_visit_time(visit: dict) -> datetime:
        """Parse visit timestamp; returns datetime.min on failure."""
        for key in ("created_at", "date"):
            val = visit.get(key)
            if isinstance(val, str) and val:
                try:
                    return datetime.fromisoformat(val.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    pass
        return datetime.min
