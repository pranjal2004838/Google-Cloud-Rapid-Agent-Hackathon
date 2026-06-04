# CliniqAI - Google-Native Clinical Agent

CliniqAI is a clinical workflow agent for small clinics built as a Google-native stack:
- Agent Development Kit (ADK) orchestration
- Gemini on Vertex AI for multilingual handwriting extraction
- Cloud Storage for source document traceability
- Cloud Run deployment
- MongoDB + MCP as patient memory and search layer

## Google-Native Hero Moments
1. Multilingual handwriting extraction (Hindi/English) with Gemini on Vertex AI
2. Agentic reasoning over extraction, storage, search, and safety checks
3. Tool orchestration across Cloud Storage, Gemini, alert checks, and MongoDB MCP
4. Real-time medication/allergy risk alerting before doctor confirmation

## Build Plan
See `CliniqAI_Complete_Build_Plan.md` for the full step-by-step implementation plan.

## Live Deployment

CliniqAI is deployed and live on Google Cloud Run:

**https://cliniqai-1072937704425.asia-south1.run.app**

## Deployment Guide
See `DEPLOYMENT_GUIDE.md` for the complete deployment guide with working commands, IAM permissions, and troubleshooting.
