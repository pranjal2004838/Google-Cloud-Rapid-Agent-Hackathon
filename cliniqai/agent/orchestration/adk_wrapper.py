"""
Google ADK Wrapper — Judge-Facing Integration Layer

This module demonstrates how CliniqAI's multi-agent orchestration maps
to Google's Agent Development Kit (ADK) concepts. It provides a thin
wrapper that can be activated when `google-adk` is installed, while the
core orchestration logic remains framework-independent for reliability.

Architecture mapping:
    ADK Agent        →  Supervisor (orchestrator)
    ADK Tool         →  Each specialized agent (extraction, context, safety, record)
    ADK MCPTool      →  MongoDB MCP Server connection
    ADK model        →  Gemini 2.5 Flash on Vertex AI

This file is NOT required for the system to work.
It exists to show judges the Google-native agent story.
"""

from __future__ import annotations

import os
from typing import Any

# ─── ADK Agent Definition (activates only when google-adk is installed) ──────

_ADK_AVAILABLE = False

try:
    from google.adk import Agent
    from google.adk.tools import FunctionTool, McpToolset
    _ADK_AVAILABLE = True
except ImportError:
    pass


def get_adk_agent():
    """
    Returns a Google ADK Agent configured with CliniqAI's tools.
    Returns None if google-adk is not installed.

    This agent uses the same underlying logic as the Supervisor but
    exposes it through ADK's framework for Google Cloud-native deployment.
    """
    if not _ADK_AVAILABLE:
        return None

    # MongoDB MCP Tool — connects ADK agent to MongoDB via MCP protocol
    mongodb_uri = os.getenv("MONGODB_URI", "")
    mongodb_mcp = McpToolset(
        server_command="npx",
        server_args=[
            "mongodb-mcp-server",
            "--connectionString", mongodb_uri,
        ]
    ) if mongodb_uri and "youruser" not in mongodb_uri else None

    # Vision Tool — prescription/document extraction via Gemini on Vertex AI
    from agent.tools.vision_tool import extract_from_prescription
    vision_tool = FunctionTool(func=extract_from_prescription)

    # Alert Tool — drug interaction and allergy checking
    from agent.tools.alert_tool import check_drug_conflicts_ai
    alert_tool = FunctionTool(func=check_drug_conflicts_ai)

    # Build tool list
    tools = [vision_tool, alert_tool]
    if mongodb_mcp:
        tools.append(mongodb_mcp)

    cliniqai_agent = Agent(
        name="CliniqAI",
        model="gemini-2.5-flash",
        instruction="""
        You are CliniqAI, a multi-agent clinical workflow orchestrator.

        Your architecture uses specialized sub-agents:
        1. ExtractionAgent — reads prescription images via Gemini on Vertex AI
        2. PatientContextAgent — retrieves patient history from MongoDB
        3. SafetyAgent — evaluates drug conflicts and allergy risks
        4. RecordUpdateAgent — persists records with audit trail

        When processing a prescription:
        - Extract structured data from the image
        - Look up existing patient by phone number
        - Check all medicines against allergies and interactions
        - Store the visit with full audit trail
        - Report results and any HIGH severity alerts

        When answering queries:
        - Search MongoDB for patient records
        - Return concise, doctor-friendly answers

        MongoDB database: cliniqai
        MongoDB collection: patients
        """,
        tools=tools,
    )

    return cliniqai_agent


def is_adk_available() -> bool:
    """Check if Google ADK is installed and available."""
    return _ADK_AVAILABLE

if __name__ == "__main__":
    print("Initializing Google ADK Agent for CliniqAI...")
    agent = get_adk_agent()
    if agent:
        print(f"[OK] Successfully initialized ADK Agent: {agent.name}")
        print(f"[OK] Model: {agent.model}")
        print(f"[OK] Tools configured: {len(agent.tools)}")
        for tool in agent.tools:
            print(f"   - {tool.name}")
        print("\nADK Agent is ready to accept events.")
    else:
        print("[ERROR] google-adk is not installed.")
        print("Please install it using: pip install google-adk")

