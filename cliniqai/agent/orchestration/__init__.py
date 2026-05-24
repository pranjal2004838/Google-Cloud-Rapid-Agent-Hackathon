"""
CliniqAI Multi-Agent Orchestration Layer

Architecture: 1 Supervisor + 4 Specialized Agents
- ExtractionAgent: reads documents (vision_tool)
- PatientContextAgent: retrieves patient history (MongoDB / in-memory)
- SafetyAgent: evaluates drug conflicts (alert_tool)
- RecordUpdateAgent: persists records + audit trail

All agents communicate through a shared typed WorkflowState.
Each agent writes ONLY to its own slot in the state.
"""

from agent.orchestration.supervisor import Supervisor
from agent.orchestration.state import WorkflowState

__all__ = ["Supervisor", "WorkflowState"]
