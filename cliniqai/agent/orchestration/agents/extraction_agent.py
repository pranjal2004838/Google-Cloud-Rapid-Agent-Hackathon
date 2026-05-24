"""
ExtractionAgent — Single Verb: READS

Responsibilities:
- Takes raw image bytes and extracts structured medical data
- Normalizes output into ExtractedData schema
- Reports confidence scores per field

Hard Boundaries (what this agent must NOT do):
- Must NOT check drug allergies or interactions
- Must NOT query the patient database
- Must NOT write any records
- Must NOT decide whether something is safe or unsafe
"""

from __future__ import annotations

import asyncio

from agent.orchestration.state import ExtractedData, Medicine, WorkflowState


class ExtractionAgent:
    """
    Wraps the vision_tool to produce a validated ExtractedData object.
    Accepts an optional extraction_fn for dependency injection (testing).
    """

    def __init__(self, extraction_fn=None):
        """
        Args:
            extraction_fn: Callable(image_bytes) -> dict.
                           Defaults to vision_tool.extract_from_prescription.
        """
        if extraction_fn is None:
            from agent.tools.vision_tool import extract_from_prescription
            self._extract = extract_from_prescription
        else:
            self._extract = extraction_fn

    async def run(self, state: WorkflowState, image_bytes: bytes) -> WorkflowState:
        """
        Execute extraction and write ONLY to state.extracted_data.

        Returns the updated state. If extraction fails, sets extracted_data
        with an error flag but does NOT raise — the supervisor handles errors.
        """
        # Run sync extraction off the event loop so Supervisor can parallelize safely.
        raw = await asyncio.to_thread(self._extract, image_bytes)

        if "error" in raw:
            state.extracted_data = ExtractedData(
                raw_extraction=raw,
                confidence_scores={"_error": raw.get("error", "unknown")}
            )
            return state

        # Normalize medicines into canonical Medicine schema
        medicines = []
        for m in raw.get("medicines", []):
            medicines.append(Medicine(
                name=m.get("name", ""),
                dose=m.get("dose"),
                frequency=m.get("frequency"),
                duration=m.get("duration"),
                confidence=None,  # set below from confidence block
            ))

        # Extract per-medicine confidence if available
        conf = raw.get("confidence", {})
        med_confidences = conf.get("medicines", [])
        for i, med in enumerate(medicines):
            if i < len(med_confidences) and isinstance(med_confidences[i], dict):
                med.confidence = med_confidences[i].get("name")

        state.extracted_data = ExtractedData(
            patient_name=raw.get("patient_name", "Unknown"),
            patient_age=_safe_int(raw.get("patient_age")),
            patient_gender=raw.get("patient_gender"),
            visit_date=raw.get("visit_date"),
            doctor_name=raw.get("doctor_name"),
            clinic_name=raw.get("clinic_name"),
            diagnosis=raw.get("diagnosis", []),
            medicines=medicines,
            tests_ordered=raw.get("tests_ordered", []),
            allergies_mentioned=raw.get("allergies_mentioned", []),
            notes=raw.get("notes"),
            confidence_scores=conf,
            raw_extraction=raw,
        )

        return state


def _safe_int(value) -> int | None:
    """Convert a value to int safely, return None on failure."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
