# GCP Services Integration (Phase 1 & Phase 2)

This document details the newly integrated GCP Services that turn CliniqAI into a production-grade, highly scalable, and secure system.

## 1. Cloud Logging + Cloud Monitoring (Observability)
**File**: `cliniqai/agent/gcp/logger.py`
- **What it does**: Seamlessly attaches Google Cloud Logging to Python's native logging module.
- **Where it's used**: Across `server.py`, `safety_agent.py`, `record_update_agent.py`.
- **Value**: Instead of prints vanishing, every workflow step (e.g., "Safety check: 2 alerts found") is pushed to GCP. If a timeout occurs, you can debug it instantly in the Cloud Console.

## 2. Cloud KMS (Security & Compliance)
**File**: `cliniqai/agent/gcp/kms.py`
- **What it does**: Handles symmetric encryption/decryption using Google Cloud Key Management Service.
- **Where it's used**: 
  - In `RecordUpdateAgent`: Encrypts sensitive PII (Name, Age, Gender) *before* saving to MongoDB.
  - In `server.py`: Transparently decrypts PII when returning data to authorized doctors.
- **Value**: Ensures HIPAA/DPDP compliance. If your MongoDB is ever breached, hackers only get encrypted gibberish.

## 3. Cloud Tasks (Scalability & UX)
**File**: `cliniqai/agent/gcp/tasks.py` & `server.py` (`/process_async`)
- **What it does**: Enqueues processing jobs into GCP infrastructure instead of blocking the user's HTTP request.
- **Where it's used**: New `/process_async` endpoint allows the doctor to upload an image and instantly get a "Processing..." response.
- **Value**: Can handle thousands of simultaneous uploads across 1,000 clinics. Prevents UI timeouts when Gemini takes 5-10 seconds to read a large document.

## 4. Cloud Pub/Sub (Real-Time Safety)
**File**: `cliniqai/agent/gcp/pubsub.py`
- **What it does**: A high-throughput messaging queue for real-time events.
- **Where it's used**: `SafetyAgent` immediately publishes a message to the `cliniqai-alerts` topic if it finds a "HIGH" severity drug conflict (e.g., Penicillin allergy).
- **Value**: Ensures doctors get life-saving alerts instantly, rather than waiting for a database refresh.
