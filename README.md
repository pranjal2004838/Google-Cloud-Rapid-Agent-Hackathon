# CliniqAI - Google-Native Clinical Agent

CliniqAI is a clinical workflow agent for small clinics built as a Google-native stack:
- **Agent Development Kit (ADK)** orchestration
- **Gemini on Vertex AI** for multilingual handwriting extraction
- **Cloud Storage** for source document traceability
- **Cloud Run** deployment
- **MongoDB + MCP** as patient memory and search layer

---

## Live Deployment

CliniqAI is deployed and live on Google Cloud Run:

**👉 [https://cliniqai-1072937704425.asia-south1.run.app](https://cliniqai-1072937704425.asia-south1.run.app) 👈**

---

## Google-Native Hero Moments
1. **Multilingual Handwriting Extraction**: Gemini on Vertex AI extracts structured clinical information from handwritten English/Hindi prescriptions.
2. **Agentic Reasoning**: Automatically orchestrates extraction, validation, storage, and safety check workflows.
3. **Tool Orchestration**: Seamless integration across Google Cloud Storage, Gemini, and MongoDB Atlas MCP.
4. **Real-time Safety Alerting**: Flags medication interactions and known patient allergies before the doctor confirms treatment.

---

## Application Walkthrough & Important Screens

Below is an overview of the key screens and features of CliniqAI.

### 1. Landing Page
The landing page introduces CliniqAI's mission to prevent medication errors in rural India by consolidating fragmented clinical records under a single mobile number. It includes:
* **The Reality**: Stat cards highlighting clinical fragmentation and preventable deaths.
* **The Case Study**: A visual timeline of Priya's composite case demonstrating the risk of drug-to-drug interactions.
* **How It Works**: A step-by-step breakdown of prescription upload, Gemini extraction, conflict checking, and record unification.

![Landing Page](docs/screenshots/landing.png)

---

### 2. Login Page
CliniqAI features a dual-login system designed for both clinical practitioners and patients. It supports language selection (English, Hindi, Bengali, Telugu, Marathi, and Tamil).

* **Clinic Mode**: Prefilled with demo credentials (`DR_DEMO_001`, `HSP_MUMBAI_001`, `demo123`) for fast hackathon testing.
* **Patient Mode**: Prefilled with Priya Sharma's registered number (`9876543210`) and OTP (`1234`).

| Clinic Login | Patient Login |
| :---: | :---: |
| ![Clinic Login](docs/screenshots/login_clinic.png) | ![Patient Login](docs/screenshots/login_patient.png) |

---

### 3. Clinic Dashboard
The main control center for doctors and clinic staff. It lists active patients, provides search functionality by phone number, and displays quick action tabs.
* **Patient Search**: Instantly look up patients by their 10-digit mobile number.
* **Active Patient List**: A sidebar showing patients currently in the clinic queue.
* **Doctor Profile**: Contextual information about the logged-in practitioner and clinic.

![Clinic Dashboard](docs/screenshots/hospital_dashboard.png)

---

### 4. Patient Clinical File (Doctor's View)
When a doctor opens a patient's file, they see a comprehensive medical dashboard:
* **Patient Summary**: Displays known allergies, age, gender, and chronic conditions.
* **Chronological Visit Timeline**: Each visit shows diagnosis, symptoms, prescribed medications, and doctor details.
* **Original Prescription Viewer**: Doctors can view the original uploaded handwritten prescription with signatures in a lightbox.
* **Reports Gallery**: Lists clinical reports (e.g., blood tests, X-rays, MRIs) with the ability to upload new reports.
* **Clinical Assistant Chat**: An AI chat interface that helps doctors analyze patient history, search through old records, and verify clinical details.

![Patient Detail View](docs/screenshots/patient_detail.png)

---

### 5. Patient Portal
The patient-facing interface accessible via OTP. It empowers patients to own and manage their medical records:
* **Health Summary**: Easy-to-read list of conditions and allergies.
* **Prescriptions & Reports**: View all past prescriptions and clinical reports uploaded by various clinics.
* **Access Permissions**: Displays active temporary access grants for cross-hospital clinical review, with a "Revoke" button to remove access immediately.
* **AI Health Assistant**: Patients can ask the AI about dosage instructions, drug functions, or general medical queries based on their records.

![Patient Portal](docs/screenshots/patient_portal.png)

---

## Build Plan & Guides
* For the full implementation process, see [CliniqAI_Complete_Build_Plan.md](file:///c:/Users/anurag/.gemini/antigravity/scratch/Google-Cloud-Rapid-Agent-Hackathon/CliniqAI_Complete_Build_Plan.md).
* For detailed deployment instructions, see [DEPLOYMENT_GUIDE.md](file:///c:/Users/anurag/.gemini/antigravity/scratch/Google-Cloud-Rapid-Agent-Hackathon/DEPLOYMENT_GUIDE.md).
