<div align="center">

# 🏥 CliniqAI
### *AI-Powered Clinical Agent for the 95% of Clinics That Have Nothing*

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-Cloud_Run-4285F4?style=for-the-badge)](https://cliniqai-1072937704425.asia-south1.run.app)
[![Google ADK](https://img.shields.io/badge/Google_ADK-Powered-34A853?style=for-the-badge&logo=google)](https://cloud.google.com/vertex-ai)
[![Gemini on Vertex AI](https://img.shields.io/badge/Gemini-Vertex_AI-FF6D00?style=for-the-badge&logo=google-cloud)](https://cloud.google.com/vertex-ai)
[![MongoDB Atlas MCP](https://img.shields.io/badge/MongoDB_Atlas-MCP_Layer-00ED64?style=for-the-badge&logo=mongodb)](https://www.mongodb.com/atlas)
[![Cloud Run](https://img.shields.io/badge/Deployed-Cloud_Run-4285F4?style=for-the-badge&logo=google-cloud)](https://cloud.run)

**👉 [TRY IT LIVE RIGHT NOW](https://cliniqai-1072937704425.asia-south1.run.app) 👈**

> *Demo credentials pre-filled. Just click Login.*

</div>

---

## 🎬 Demo Video

> **[▶ Watch the 3-Minute Demo](https://cliniqai-1072937704425.asia-south1.run.app)** — See CliniqAI prevent a drug interaction in real time, across clinics, in Hindi.

[![Demo Preview](docs/screenshots/landing.png)](https://cliniqai-1072937704425.asia-south1.run.app)

---

## 🚨 The Problem — A Life-or-Death Gap in Healthcare

**India has 1.3 million small clinics. 95% of them use paper registers.**

This is not an inconvenience. It kills people.

| Reality | Scale |
|:--------|:------|
| 💊 Preventable drug interactions | 5.6 million hospitalizations/year |
| 📋 Patients visiting 2+ clinics with no shared records | Every rural patient, every day |
| 🗒️ Paper registers with no allergy history | 95% of India's 1,300,000 clinics |
| 💸 Existing EHR systems (Epic, Cerner) cost | $370,000+ per year to implement |

**The gap:** Big hospitals get expensive EHR systems. Small clinics get nothing.  
**CliniqAI fills that gap — completely free, deployed in 5 minutes.**

---

## 💡 The Solution — CliniqAI

CliniqAI is a **Google-native agentic clinical system** that gives small clinics the power of a hospital-grade patient management system, powered by Gemini AI, at zero cost.

**One photo of a handwritten prescription → complete patient intelligence in seconds.**

```
📸 Doctor photographs handwritten Hindi prescription
          ↓
🧠 Gemini on Vertex AI reads + extracts structured data  
          ↓
🔍 MongoDB MCP searches patient's full cross-clinic history
          ↓
⚠️  ALERT: "Patient has Penicillin allergy — prescribed Amoxicillin!"
          ↓
✅ Doctor changes medication. Patient is safe.
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CLINIQAI SYSTEM                      │
│                                                             │
│  📱 Web Client (Clinic + Patient Portal)                    │
│       │                                                     │
│       ▼                                                     │
│  ☁️  Cloud Run (FastAPI Backend)                            │
│       │                                                     │
│       ├──► 🤖 ADK Agent Orchestrator                        │
│       │         │                                           │
│       │         ├──► 🧠 Gemini on Vertex AI                 │
│       │         │    (Handwriting OCR, Hindi/English)       │
│       │         │                                           │
│       │         ├──► 🗄️  Cloud Storage                     │
│       │         │    (Original prescription archive)        │
│       │         │                                           │
│       │         └──► 🍃 MongoDB Atlas via MCP               │
│       │              (Patient memory + vector search)       │
│       │                                                     │
│       └──► ⚠️  Safety Alert Engine                          │
│                (Drug interactions + allergy checks)         │
└─────────────────────────────────────────────────────────────┘
```

**Full Stack:**
| Layer | Technology |
|:------|:-----------|
| Agent Orchestration | **Google Agent Development Kit (ADK)** |
| AI / OCR | **Gemini 2.0 Flash on Vertex AI** |
| Patient Memory | **MongoDB Atlas + MCP Server** |
| Document Storage | **Google Cloud Storage** |
| Deployment | **Google Cloud Run** |
| Backend | **Python + FastAPI** |

---

## ✨ Google-Native Hero Features

### 1. 🖊️ Multilingual Handwriting Extraction *(Gemini on Vertex AI)*
Upload a photo of a handwritten prescription in **English, Hindi, Bengali, Telugu, Marathi, or Tamil**. Gemini extracts diagnosis, medications, dosages, and doctor notes — zero manual typing.

### 2. 🤖 Agentic Workflow Orchestration *(Google ADK)*
The ADK agent automatically orchestrates extraction → validation → storage → safety-check as a seamless pipeline. No human coordination required.

### 3. ⚠️ Real-Time Drug Safety Alerting
Before a doctor confirms any treatment, CliniqAI cross-checks:
- Known patient allergies (from any past clinic)
- Active medications (duplicate prescriptions)
- Drug-to-drug interaction flags

### 4. 🔍 Cross-Clinic Patient Intelligence *(MongoDB Atlas MCP)*
A patient's full history — from every clinic they've ever visited — unified under their mobile number. One phone number = one permanent medical record.

### 5. 🔐 Patient-Controlled Access
Patients grant and revoke clinic access in real time. Complete data sovereignty — patients own their records.

---

## 🎯 Impact Metrics

| Metric | Value |
|:-------|:------|
| Target Market | 1.3M small clinics in India |
| Addressable Patients | 800M+ in India's rural/semi-urban areas |
| Cost to Implement | **₹0 (Free)** |
| Setup Time | **5 minutes** |
| Languages Supported | 6 (English, Hindi, Bengali, Telugu, Marathi, Tamil) |
| Prescription Read Time | **< 3 seconds** |

---

## 📱 Application Walkthrough

### Landing Page — *The Problem Made Visceral*
Real statistics, a timeline of a composite patient case (Priya), and a clear "How It Works" — judges understand the why in 30 seconds.

![Landing Page](docs/screenshots/landing.png)

---

### Dual Login — *Clinic Mode & Patient Mode*
Pre-filled demo credentials for instant hackathon testing. No setup friction.

| Clinic Login | Patient Login |
|:---:|:---:|
| ![Clinic Login](docs/screenshots/login_clinic.png) | ![Patient Login](docs/screenshots/login_patient.png) |

> **Demo Credentials:**
> - **Clinic:** `DR_DEMO_001` / `HSP_MUMBAI_001` / `demo123`  
> - **Patient:** Mobile `9876543210` → OTP `1234`

---

### Clinic Dashboard — *Doctor's Command Center*
Search patients by phone number, view the active queue, and open any patient file instantly.

![Clinic Dashboard](docs/screenshots/hospital_dashboard.png)

---

### Patient Clinical File — *Complete Medical Intelligence*
Every visit, every prescription, every test, every allergy — in one screen. With the **AI Clinical Assistant** chat for deep patient history queries.

![Patient Detail View](docs/screenshots/patient_detail.png)

---

### Patient Portal — *Patients Own Their Data*
Patients view all records from all clinics, manage access permissions, and chat with the AI health assistant about their own medications.

![Patient Portal](docs/screenshots/patient_portal.png)

---

## ⚡ Quick Start — Run in 3 Steps

```bash
# 1. Clone the repository
git clone https://github.com/your-username/Google-Cloud-Rapid-Agent-Hackathon.git
cd Google-Cloud-Rapid-Agent-Hackathon

# 2. Set up environment
cp .env.example .env
# Fill in: GOOGLE_CLOUD_PROJECT, MONGODB_URI, VERTEX_AI_LOCATION

# 3. Run locally
pip install -r requirements.txt
python -m uvicorn cliniqai.main:app --reload
```

**Or just use the live deployment → [https://cliniqai-1072937704425.asia-south1.run.app](https://cliniqai-1072937704425.asia-south1.run.app)**

---

## 🔧 Environment Variables

```env
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
VERTEX_AI_LOCATION=asia-south1
GCS_BUCKET_NAME=your-prescriptions-bucket
MONGODB_URI=your-mongodb-atlas-connection-string
MONGODB_DB_NAME=cliniqai
```

---

## 🚧 Challenges We Solved

| Challenge | How We Solved It |
|:----------|:----------------|
| Handwritten Hindi OCR accuracy | Few-shot prompting with Gemini + structured output validation |
| Cross-clinic record unification without login | Patient identified by mobile number as universal key |
| Real-time safety alerts before doctor confirmation | ADK agent pipeline with blocking safety check gate |
| Zero-latency MCP tool calls | Connection pooling + async MongoDB Atlas MCP server |
| Multilingual UI for non-English doctors | Dynamic language selection at login, persisted in session |

---

## 🔮 What's Next — The Roadmap

- [ ] **WhatsApp Integration** — Doctors upload prescription photos via WhatsApp bot
- [ ] **Voice-First Interface** — Hindi voice commands for rural doctors with low digital literacy  
- [ ] **Government Health Scheme Linking** — ABHA (Ayushman Bharat Health Account) integration
- [ ] **Predictive Analytics** — Population-level disease trend detection from anonymized data
- [ ] **Pharmacy Connect** — Auto-send verified prescriptions to the nearest pharmacy

---

## 👥 Team

Built with ❤️ for the **Google Cloud Rapid Agent Hackathon**

> *"We didn't build another hospital EHR. We built the thing that 95% of clinics in the world actually need — something free, mobile, multilingual, and intelligent."*

---

## 📄 Additional Documentation

| Document | Description |
|:---------|:------------|
| [Complete Build Plan](CliniqAI_Complete_Build_Plan.md) | Full technical implementation guide |
| [Deployment Guide](DEPLOYMENT_GUIDE.md) | Step-by-step Google Cloud deployment |
| [Why CliniqAI is Different](WHY_CLINIQAI_IS_DIFFERENT.md) | Market positioning & competitive analysis |
| [Phase 2: HIE Implementation](PHASE_2_HIE_IMPLEMENTATION.md) | Health Information Exchange roadmap |

---

<div align="center">

**Built on Google Cloud · Powered by Gemini · Deployed on Cloud Run**

[![Made with Gemini](https://img.shields.io/badge/Made_with-Gemini_AI-4285F4?style=flat-square&logo=google)](https://deepmind.google/technologies/gemini/)
[![Google ADK](https://img.shields.io/badge/Google-ADK-34A853?style=flat-square)](https://cloud.google.com/vertex-ai)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas_MCP-00ED64?style=flat-square&logo=mongodb)](https://mongodb.com)

*For 800 million patients who deserve better healthcare.*

</div>
