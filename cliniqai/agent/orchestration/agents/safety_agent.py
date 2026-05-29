"""
SafetyAgent — Single Verb: EVALUATES

Responsibilities:
- Compares new medicines against patient allergies
- Checks drug-drug interactions with current medications
- Detects cross-reactivity between drug families
- Produces structured alerts with severity and override requirements

Hard Boundaries (what this agent must NOT do):
- Must NOT read or interpret prescription images
- Must NOT query the patient database
- Must NOT write or update any records
- Must NOT generate final doctor-facing summaries
"""

from __future__ import annotations

import asyncio

from agent.orchestration.state import Alert, SafetyAssessment, WorkflowState
from agent.gcp.pubsub import publish_alert
from agent.gcp.logger import get_logger

logger = get_logger(__name__)


class SafetyAgent:
    """
    Evaluates medication safety using the alert_tool.
    Accepts an optional check_fn for dependency injection (testing).
    """

    def __init__(self, check_fn=None):
        """
        Args:
            check_fn: Callable(patient_allergies, current_medicines, new_medicines) -> dict.
                      Defaults to alert_tool.check_drug_conflicts_ai (with rule-based fallback).
        """
        if check_fn is None:
            from agent.tools.alert_tool import check_drug_conflicts_ai
            self._check = check_drug_conflicts_ai
        else:
            self._check = check_fn

    async def run(self, state: WorkflowState) -> WorkflowState:
        """
        Execute safety evaluation and write ONLY to state.safety_assessment.
        Requires state.extracted_data and state.patient_context to be set.
        """
        extracted = state.extracted_data
        context = state.patient_context

        if extracted is None or context is None:
            state.safety_assessment = SafetyAssessment()
            return state

        # Build inputs in the format alert_tool expects
        patient_allergies = context.all_allergies
        current_medicines = [
            {"name": m.name, "dose": m.dose}
            for m in context.current_medicines
        ]
        new_medicines = [
            {"name": m.name, "dose": m.dose}
            for m in extracted.medicines
        ]

        # Run the check (AI-powered with rule-based fallback)
        result = await asyncio.to_thread(
            self._check,
            patient_allergies=patient_allergies,
            current_medicines=current_medicines,
            new_medicines=new_medicines,
        )

        # Normalize alerts into canonical Alert schema
        alerts: list[Alert] = []
        for raw_alert in result.get("alerts", []):
            severity = raw_alert.get("severity", "MEDIUM")
            alerts.append(Alert(
                severity=severity,
                type=raw_alert.get("type", "UNKNOWN"),
                message=raw_alert.get("message", ""),
                evidence=raw_alert.get("evidence"),
                requires_override=(severity == "HIGH"),
            ))

        has_alerts = len(alerts) > 0
        high_count = sum(1 for a in alerts if a.severity == "HIGH")

        # Publish critical alerts via Pub/Sub for real-time notification
        if has_alerts:
            logger.info(f"SafetyAgent found {len(alerts)} alerts. Publishing to Pub/Sub.")
            for alert in alerts:
                if alert.severity == "HIGH":
                    patient_id = getattr(context, 'patient_id', "unknown")
                    publish_alert(
                        alert_type=alert.type,
                        message=alert.message,
                        patient_id=str(patient_id)
                    )

        state.safety_assessment = SafetyAssessment(
            has_alerts=has_alerts,
            alert_count=len(alerts),
            high_severity_count=high_count,
            alerts=alerts,
            requires_override=(high_count > 0),
        )

        return state
