# CliniqAI - Phase 3 Deployment Guide

> **Project**: Google Cloud Rapid Agent Hackathon  
> **Service**: CliniqAI  
> **GCP Project ID**: `project-21005770-1368-4c5d-8ea`  
> **Region**: `asia-south1` (Mumbai)  
> **Final Live URL**: https://cliniqai-1072937704425.asia-south1.run.app  
> **Date Deployed**: 2026-06-03

---

## Table of Contents

1. [Pre-Deployment Checklist](#1-pre-deployment-checklist)
2. [Required IAM Permissions](#2-required-iam-permissions)
3. [Step-by-Step Deployment Commands](#3-step-by-step-deployment-commands)
4. [Problems Faced & Solutions](#4-problems-faced--solutions)
5. [Post-Deployment Verification](#5-post-deployment-verification)

---

## 1. Pre-Deployment Checklist

Before running any commands, ensure you have the following:

| Resource | Value | Source |
|----------|-------|--------|
| **GCP Project ID** | `project-21005770-1368-4c5d-8ea` | Google Cloud Console |
| **Gemini API Key** | `AIzaSyAFQiu-kOL6zeV1bGd9pJAXM3VC2l4_CV4` | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| **MongoDB URI** | `mongodb+srv://4cp4dor_db_user:OYyOtAi1HpE01UQU@cluster0.wsiijwl.mongodb.net/cliniqai?retryWrites=true&w=majority` | [MongoDB Atlas](https://cloud.mongodb.com) |
| **GCS Bucket** | `cliniqai-uploads-project-21005770-1368` | Created in GCP |
| **Region** | `asia-south1` | GCP Region |

---

## 2. Required IAM Permissions

The Cloud Build / Compute Service Account (`1072937704425-compute@developer.gserviceaccount.com`) needs the following roles:

| Role | Purpose |
|------|---------|
| `Storage Object Viewer` | Read source code from Cloud Storage |
| `Storage Object Creator` | Write source code to Cloud Storage |
| `Artifact Registry Service Agent` | Push/pull container images |
| `Artifact Registry Writer` | Write container images to Artifact Registry |
| `Cloud Run Admin` | Deploy and manage Cloud Run services |
| `Cloud Build Service Account` | Execute Cloud Build jobs |

### How to Add IAM Roles:
1. Go to [GCP Console](https://console.cloud.google.com) > **IAM & Admin** > **IAM**
2. Find the service account: `1072937704425-compute@developer.gserviceaccount.com`
3. Click **Edit** (pencil icon)
4. Click **+ Add Another Role**
5. Add each role listed above
6. Click **Save**

---

## 3. Step-by-Step Deployment Commands

> **Environment**: Google Cloud Shell  
> **Working Directory**: `~/Google-Cloud-Rapid-Agent-Hackathon`

### Step 1: Clone the Repository

```bash
cd ~
git clone https://github.com/pranjal2004838/Google-Cloud-Rapid-Agent-Hackathon.git
cd Google-Cloud-Rapid-Agent-Hackathon
```

### Step 2: Set Environment Variables

```bash
export PROJECT_ID="project-21005770-1368-4c5d-8ea"
export REGION="asia-south1"
export GEMINI_KEY="AIzaSyAFQiu-kOL6zeV1bGd9pJAXM3VC2l4_CV4"
export MONGODB_URI="mongodb+srv://4cp4dor_db_user:OYyOtAi1HpE01UQU@cluster0.wsiijwl.mongodb.net/cliniqai?retryWrites=true&w=majority"
export GCS_BUCKET="cliniqai-uploads-project-21005770-1368"
```

### Step 3: Set GCP Project

```bash
gcloud config set project $PROJECT_ID
```

### Step 4: Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  kms.googleapis.com \
  pubsub.googleapis.com \
  cloudtasks.googleapis.com \
  storage.googleapis.com \
  aiplatform.googleapis.com \
  cloudbuild.googleapis.com
```

### Step 5: Create Cloud KMS Keyring and Key

```bash
gcloud kms keyrings create cliniqai-keyring \
  --location $REGION

gcloud kms keys create patient-data-key \
  --location $REGION \
  --keyring cliniqai-keyring \
  --purpose encryption
```

### Step 6: Create Cloud Storage Bucket

```bash
gcloud storage buckets create gs://$GCS_BUCKET \
  --location $REGION
```

### Step 7: Create Cloud Pub/Sub Topic

```bash
gcloud pubsub topics create cliniqai-alerts
```

### Step 8: Create Cloud Tasks Queue

```bash
gcloud tasks queues create cliniqai-queue \
  --location $REGION
```

### Step 9: Build Docker Image with Cloud Build

> **Note**: We use `cloudbuild.yaml` (which uses the Dockerfile) instead of Buildpacks.

```bash
gcloud builds submit --config cloudbuild.yaml --region $REGION
```

Wait for `STATUS: SUCCESS` before proceeding.

### Step 10: Deploy to Cloud Run

```bash
gcloud run deploy cliniqai \
  --image asia-south1-docker.pkg.dev/$PROJECT_ID/cloud-run-source-deploy/cliniqai:latest \
  --region $REGION \
  --allow-unauthenticated \
  --platform managed \
  --memory 512Mi \
  --cpu 1 \
  --timeout 3600 \
  --max-instances 20
```

### Step 11: Set Environment Variables

```bash
gcloud run services update cliniqai \
  --region $REGION \
  --set-env-vars GOOGLE_API_KEY="$GEMINI_KEY" \
  --set-env-vars MONGODB_URI="$MONGODB_URI" \
  --set-env-vars GOOGLE_CLOUD_PROJECT="$PROJECT_ID" \
  --set-env-vars GOOGLE_CLOUD_LOCATION="$REGION" \
  --set-env-vars GCS_UPLOAD_BUCKET="$GCS_BUCKET" \
  --set-env-vars KMS_KEY_RING="cliniqai-keyring" \
  --set-env-vars KMS_KEY_NAME="patient-data-key"
```

### Step 12: Get Service URL

```bash
gcloud run services describe cliniqai --region $REGION --format='value(status.url)'
```

---

## 4. Problems Faced & Solutions

### Problem 1: Docker Push Failing from Cloud Shell
- **Error**: `dial tcp 74.125.68.82:443: connect: connection refused`
- **Cause**: Cloud Shell has network restrictions that block outbound Docker pushes to GCR
- **Solution**: Use `gcloud builds submit` with `cloudbuild.yaml` instead of local Docker push. Cloud Build runs inside GCP's internal network.

### Problem 2: Buildpacks Ignoring Dockerfile
- **Error**: `failed to build: for Python, provide a main.py or app.py file`
- **Cause**: Cloud Run's `--source .` flag defaults to Buildpacks, which auto-detects the project type and ignores the Dockerfile
- **Solution**: Create a `cloudbuild.yaml` file that explicitly uses `docker build` with the Dockerfile, then use `gcloud builds submit --config cloudbuild.yaml`

### Problem 3: Wrong NPM Package Name in Dockerfile
- **Error**: `npm ERR! 404 '@modelcontextprotocol/server-mongodb@*' is not in this registry`
- **Cause**: Incorrect package name in Dockerfile
- **Solution**: Changed `npm install -g @modelcontextprotocol/server-mongodb` to `npm install -g mongodb-mcp-server`

### Problem 4: PYTHONPATH Not Set (ModuleNotFoundError)
- **Error**: `ModuleNotFoundError: No module named 'agent'`
- **Cause**: Python couldn't find the `agent` module because it was inside `/app/cliniqai/` but the working directory was `/app`
- **Solution**: Added `ENV PYTHONPATH=/app/cliniqai:$PYTHONPATH` to the Dockerfile

### Problem 5: Missing Python Package (google-generativeai)
- **Error**: `ModuleNotFoundError: No module named 'google.generativeai'`
- **Cause**: `google-generativeai` was not listed in `requirements.txt`
- **Solution**: Added `google-generativeai>=0.8.0` to `requirements.txt`

### Problem 6: Max Instances Quota Exceeded
- **Error**: `Max instances must be set to 20 or fewer`
- **Cause**: GCP student/hackathon accounts have a quota limit of 20 max instances per region
- **Solution**: Reduced `--max-instances` from 100 to 20

### Problem 7: Cloud Build Service Account Missing Permissions
- **Error**: `Permission 'storage.objects.get' denied on resource`
- **Cause**: The default compute service account lacked IAM permissions
- **Solution**: Added `Storage Object Viewer`, `Storage Object Creator`, `Artifact Registry Service Agent`, and `Artifact Registry Writer` roles in the IAM console

---

## 5. Post-Deployment Verification

### Check Service Status
```bash
gcloud run services describe cliniqai --region asia-south1
```

### View Live Logs
```bash
gcloud run logs read cliniqai --region asia-south1 --limit 50
```

### Access the Application
- **Main Service**: https://cliniqai-1072937704425.asia-south1.run.app
- **Hospital Dashboard**: https://cliniqai-1072937704425.asia-south1.run.app/ui/hospital.html
- **Patient Portal**: https://cliniqai-1072937704425.asia-south1.run.app/ui/patient.html

### Test the API
```bash
curl -X POST "https://cliniqai-1072937704425.asia-south1.run.app/process" \
  -F "phone=+919999999999" \
  -F "file=@prescription.jpg"
```

---

## Summary of Working Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Dual-runtime Docker image (Python 3.11 + Node.js) |
| `cloudbuild.yaml` | Cloud Build configuration for Dockerfile-based builds |
| `cliniqai/requirements.txt` | Python dependencies |
| `cliniqai/agent/server.py` | FastAPI server with multi-agent orchestration |

---

> **Generated with [Devin](https://cli.devin.ai/docs)**  
> Co-Authored-By: Devin <158243242+devin-ai-integration[bot]@users.noreply.github.com>
