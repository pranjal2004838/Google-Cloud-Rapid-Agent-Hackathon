# PHASE 2: Visual Guide & Diagrams

This document contains all visual diagrams and flowcharts for Phase 2.

---

## 1. User Journey Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLINIQAI USER JOURNEY                       │
└─────────────────────────────────────────────────────────────────────┘

PATIENT JOURNEY:
┌──────────────┐
│ Patient      │
│ Opens App    │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────┐
│ Landing Page                             │
│ "I'm a Patient" | "I'm a Provider"       │
└──────┬───────────────────────────────────┘
       │ Click "I'm a Patient"
       ▼
┌──────────────────────────────────────────┐
│ Patient Login - Step 1                   │
│ Enter Mobile Number                      │
│ [+91-98765-43210]                        │
│ [SEND OTP]                               │
└──────┬───────────────────────────────────┘
       │ SMS received
       ▼
┌──────────────────────────────────────────┐
│ Patient Login - Step 2                   │
│ Enter 6-digit OTP                        │
│ [____] [____] [____] [____] [____] [____]│
│ [VERIFY & LOGIN]                         │
└──────┬───────────────────────────────────┘
       │ OTP verified
       ▼
┌──────────────────────────────────────────┐
│ Patient Dashboard                        │
│ • Health Timeline                        │
│ • Active Medications                     │
│ • Allergies & Conditions                 │
│ [LOGOUT]                                 │
└──────────────────────────────────────────┘


DOCTOR JOURNEY:
┌──────────────┐
│ Doctor       │
│ Opens App    │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────┐
│ Landing Page                             │
│ "I'm a Patient" | "I'm a Provider"       │
└──────┬───────────────────────────────────┘
       │ Click "I'm a Provider"
       ▼
┌──────────────────────────────────────────┐
│ Clinic Login                             │
│ Clinic ID:   [CLINIC_001]                │
│ Doctor ID:   [DOC_001]                   │
│ Password:    [**********]                │
│ [LOGIN]                                  │
└──────┬───────────────────────────────────┘
       │ Credentials verified
       ▼
┌──────────────────────────────────────────┐
│ Clinic Dashboard                         │
│ • Patient Search                         │
│ • Document Upload                        │
│ • Alert System                           │
│ • Chatbot                                │
│ [LOGOUT]                                 │
└──────┬───────────────────────────────────┘
       │
       ├─────────────────────────────────┐
       │                                 │
       ▼                                 ▼
   ┌─────────────────┐         ┌──────────────────┐
   │ Patient Found   │         │ Patient Not      │
   │ & Authorized    │         │ Found/Auth       │
   │                 │         │                  │
   │ Show Record     │         │ Send OTP or      │
   │ Add Visit       │         │ Register         │
   └─────────────────┘         └──────────────────┘
       │                                 │
       └─────────────────────────────────┘
                     │
                     ▼
         ┌──────────────────────────┐
         │ Upload Document          │
         │ [Drop Zone]              │
         │ [EXTRACT & SAVE]         │
         └──────────┬───────────────┘
                    │
                    ▼
         ┌──────────────────────────┐
         │ Check for Conflicts      │
         │ (Gemini AI)              │
         └──────────┬───────────────┘
                    │
         ┌──────────┴──────────┐
         │                     │
         ▼                     ▼
    ┌─────────────┐    ┌──────────────┐
    │ RED ALERT   │    │ GREEN OK     │
    │ Conflict!   │    │ Safe!        │
    │ [ACK/CANCEL]│    │ [PROCEED]    │
    └─────────────┘    └──────────────┘
```

---

## 2. Authentication Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTHENTICATION FLOWS                         │
└─────────────────────────────────────────────────────────────────┘

CLINIC LOGIN (3-FACTOR):
┌──────────────────────────────────────────────────────────────┐
│ Frontend                                                     │
│ [Clinic ID] [Doctor ID] [Password]                          │
│ [LOGIN BUTTON]                                              │
└──────────────┬───────────────────────────────────────────────┘
               │ POST /api/auth/clinic-login
               │ {clinic_id, doctor_id, password}
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Backend                                                      │
│ 1. Find clinic by clinic_id                                 │
│ 2. Find doctor in clinic.doctors array                      │
│ 3. Verify password_hash (bcrypt)                            │
│ 4. Check doctor.is_active == true                           │
│ 5. Generate JWT token (24-hour expiry)                      │
│ 6. Create session record                                    │
│ 7. Return {token, doctor_info, clinic_info}                │
└──────────────┬───────────────────────────────────────────────┘
               │ {token, doctor_info, clinic_info}
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Frontend                                                     │
│ localStorage.setItem('token', token)                        │
│ localStorage.setItem('user_type', 'doctor')                 │
│ Navigate to /clinic-dashboard                              │
└──────────────────────────────────────────────────────────────┘


PATIENT OTP LOGIN (2-STEP):
┌──────────────────────────────────────────────────────────────┐
│ Frontend - Step 1                                            │
│ [Mobile Number: +91-98765-43210]                            │
│ [SEND OTP]                                                  │
└──────────────┬───────────────────────────────────────────────┘
               │ POST /api/auth/patient-send-otp
               │ {mobile_number}
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Backend                                                      │
│ 1. Validate mobile number format                            │
│ 2. Generate 6-digit OTP                                     │
│ 3. Store OTP + expiry (5 min) in DB                         │
│ 4. Send SMS: "Your code is: 654321"                         │
│ 5. Return {message, otp_expiry_seconds}                     │
└──────────────┬───────────────────────────────────────────────┘
               │ SMS received
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Frontend - Step 2                                            │
│ [____] [____] [____] [____] [____] [____]                   │
│ [VERIFY & LOGIN]                                            │
└──────────────┬───────────────────────────────────────────────┘
               │ POST /api/auth/patient-verify-otp
               │ {mobile_number, otp}
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Backend                                                      │
│ 1. Find patient by mobile_number                            │
│ 2. Verify OTP matches                                       │
│ 3. Check OTP not expired                                    │
│ 4. Mark otp_verified = true                                 │
│ 5. Generate JWT token (30-day expiry)                       │
│ 6. Create session record                                    │
│ 7. Return {token, patient_info}                             │
└──────────────┬───────────────────────────────────────────────┘
               │ {token, patient_info}
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Frontend                                                     │
│ localStorage.setItem('token', token)                        │
│ localStorage.setItem('user_type', 'patient')                │
│ Navigate to /patient-dashboard                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Cross-Clinic Authorization Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              CROSS-CLINIC AUTHORIZATION FLOW                    │
└─────────────────────────────────────────────────────────────────┘

SCENARIO: Patient moves from Clinic X to Clinic Y

STEP 1: Doctor searches for patient
┌──────────────────────────────────────────────────────────────┐
│ Clinic Y Dashboard                                           │
│ Search Patient: [+91-98765-43210]                           │
│ [SEARCH]                                                    │
└──────────────┬───────────────────────────────────────────────┘
               │ GET /api/clinic/search-patient
               │ {mobile_number, clinic_id, token}
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Backend Search Logic                                         │
│ 1. Validate JWT token                                       │
│ 2. Find patient by mobile_number                            │
│ 3. Check if clinic_id in authorized_clinics                │
└──────────────┬───────────────────────────────────────────────┘
               │
         ┌─────┴──────────────┐
         │                    │
         ▼ YES                ▼ NO
    ┌─────────────┐      ┌──────────────────┐
    │ CASE A      │      │ CASE B           │
    │ Authorized  │      │ Not Authorized   │
    │ Return full │      │ Return error     │
    │ patient     │      │ "Not authorized" │
    │ record      │      │                  │
    └──────┬──────┘      └────────┬─────────┘
           │                      │
           │                      ▼
           │            ┌──────────────────────────────┐
           │            │ Clinic Y Dashboard           │
           │            │ ⚠️ Patient not authorized    │
           │            │ [SEND AUTHORIZATION OTP]     │
           │            └────────┬─────────────────────┘
           │                     │
           │                     │ POST /api/clinic/request-patient-access
           │                     │ {mobile_number, clinic_id, doctor_id}
           │                     │
           │                     ▼
           │            ┌──────────────────────────────┐
           │            │ Backend                      │
           │            │ 1. Generate auth OTP         │
           │            │ 2. Store pending auth        │
           │            │ 3. Send SMS to patient:      │
           │            │    "Clinic Y requests access"│
           │            │    "Reply with OTP: 654321"  │
           │            └────────┬─────────────────────┘
           │                     │
           │                     ▼
           │            ┌──────────────────────────────┐
           │            │ Patient receives SMS         │
           │            │ "Clinic Y requests access"   │
           │            │ "Reply with OTP: 654321"     │
           │            │                              │
           │            │ Patient replies with OTP     │
           │            └────────┬─────────────────────┘
           │                     │
           │                     │ POST /api/patient/authorize-clinic-access
           │                     │ {mobile_number, clinic_id, otp}
           │                     │
           │                     ▼
           │            ┌──────────────────────────────┐
           │            │ Backend                      │
           │            │ 1. Verify OTP                │
           │            │ 2. Add clinic to             │
           │            │    authorized_clinics array  │
           │            │ 3. Return "Access granted"   │
           │            └────────┬─────────────────────┘
           │                     │
           │                     ▼
           │            ┌──────────────────────────────┐
           │            │ Clinic Y Dashboard           │
           │            │ ✓ Patient record now visible │
           │            │ ✓ Full history from all      │
           │            │   clinics                    │
           │            │ ✓ Can add new visit          │
           │            └──────────────────────────────┘
           │
           ▼
    ┌──────────────────────────────────────┐
    │ Clinic Y Dashboard                   │
    │ ✓ Ramesh Gupta                       │
    │ ✓ Age: 45 | Gender: Male             │
    │ ✓ Known Allergies: Penicillin        │
    │ ✓ Chronic Conditions: Diabetes       │
    │                                      │
    │ VISIT HISTORY (All Clinics):         │
    │ • 2026-05-20 | Clinic X | Fever     │
    │ • 2026-05-10 | City Hospital | HTN  │
    │ • 2026-04-15 | Apollo | Diabetes    │
    │                                      │
    │ [ADD NEW VISIT] [UPLOAD PRESCRIPTION]│
    └──────────────────────────────────────┘
```

---

## 4. Drug Conflict Detection Flow

```
┌─────────────────────────────────────────────────────────────────┐
│           DRUG CONFLICT DETECTION FLOW (THE WOW MOMENT)         │
└─────────────────────────────────────────────────────────────────┘

STEP 1: Doctor uploads prescription
┌──────────────────────────────────────────────────────────────┐
│ Clinic Dashboard - Upload Zone                               │
│ [Drop prescription photo here]                               │
│ [EXTRACT & SAVE TO RECORDS]                                 │
└──────────────┬───────────────────────────────────────────────┘
               │ POST /api/clinic/upload-document
               │ {file, mobile_number, clinic_id, token}
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Backend                                                      │
│ 1. Store file in Cloud Storage                              │
│ 2. Return document_id                                       │
└──────────────┬───────────────────────────────────────────────┘
               │
               ▼
STEP 2: Gemini extracts data
┌──────────────────────────────────────────────────────────────┐
│ Backend                                                      │
│ POST /api/clinic/extract-document                           │
│ {document_id, mobile_number, token}                         │
│                                                              │
│ 1. Read image from Cloud Storage                            │
│ 2. Call Gemini Vision API                                   │
│ 3. Extract:                                                 │
│    - Patient name                                           │
│    - Medicines: [Amoxicillin 500mg 2x/day]                 │
│    - Diagnosis: Fever                                       │
│    - Doctor name                                            │
│    - Date                                                   │
└──────────────┬───────────────────────────────────────────────┘
               │
               ▼
STEP 3: Check for conflicts
┌──────────────────────────────────────────────────────────────┐
│ Backend - Alert Tool                                         │
│                                                              │
│ Get patient's history:                                      │
│ - Known allergies: [Penicillin]                            │
│ - Current medicines: [Amlodipine, Metformin]               │
│ - Past medicines: [Amoxicillin (from Clinic X)]            │
│                                                              │
│ Check extracted medicines against:                          │
│ 1. Direct allergy match                                     │
│ 2. Cross-allergy match                                      │
│ 3. Drug-drug interactions                                   │
│                                                              │
│ FOUND: Amoxicillin is penicillin-based                      │
│ CONFLICT: Patient allergic to Penicillin                    │
│ SEVERITY: HIGH                                              │
│ MESSAGE: "Patient allergic to Penicillin since Oct 2025"    │
└──────────────┬───────────────────────────────────────────────┘
               │ {alerts: [{severity: "HIGH", message: "..."}]}
               ▼
STEP 4: Display alert
┌──────────────────────────────────────────────────────────────┐
│ Clinic Dashboard - Alert Zone                                │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ ⚠️ CRITICAL ALERT                                      │  │
│ │                                                        │  │
│ │ ALLERGY CONFLICT: Patient allergic to Penicillin      │  │
│ │ since Oct 2025 at Apollo Hospital.                    │  │
│ │                                                        │  │
│ │ New prescription includes Amoxicillin                 │  │
│ │ (penicillin-based antibiotic).                        │  │
│ │                                                        │  │
│ │ [I ACKNOWLEDGE THIS RISK] [CANCEL PRESCRIPTION]       │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ Doctor sees RED ALERT and cancels prescription              │
│ PATIENT LIFE SAVED ✓                                        │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. Database Schema Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    MONGODB COLLECTIONS                          │
└─────────────────────────────────────────────────────────────────┘

CLINICS Collection:
┌────────────────────────────────────────┐
│ clinic_id: "CLINIC_001"                │
│ clinic_name: "Dr. Sharma's Clinic"     │
│ clinic_email: "clinic@example.com"     │
│ clinic_phone: "+91-9876543210"         │
│ clinic_address: "Mumbai, India"        │
│ clinic_password_hash: "bcrypt_hash"    │
│                                        │
│ doctors: [                             │
│   {                                    │
│     doctor_id: "DOC_001"               │
│     doctor_name: "Dr. Sharma"          │
│     department: "General Physician"    │
│     password_hash: "bcrypt_hash"       │
│     is_active: true                    │
│     last_login: ISODate                │
│   }                                    │
│ ]                                      │
│                                        │
│ created_at: ISODate                    │
│ updated_at: ISODate                    │
└────────────────────────────────────────┘


PATIENTS Collection (Mobile Number = Primary Key):
┌────────────────────────────────────────────────────────────┐
│ mobile_number: "+91-9876543210" (UNIQUE)                   │
│ patient_name: "Ramesh Gupta"                               │
│ age: 45                                                    │
│ gender: "Male"                                             │
│ blood_group: "O+"                                          │
│                                                            │
│ known_allergies: ["penicillin", "aspirin"]                │
│ chronic_conditions: ["diabetes", "hypertension"]          │
│                                                            │
│ authorized_clinics: [                                     │
│   {                                                       │
│     clinic_id: "CLINIC_001"                              │
│     clinic_name: "Dr. Sharma's Clinic"                   │
│     access_granted_date: ISODate                         │
│     access_status: "active"                              │
│     otp_verified: true                                   │
│   }                                                       │
│ ]                                                         │
│                                                            │
│ visits: [                                                 │
│   {                                                       │
│     visit_id: ObjectId                                   │
│     clinic_id: "CLINIC_001"                              │
│     doctor_id: "DOC_001"                                 │
│     visit_date: ISODate                                  │
│     diagnosis: "Viral Fever"                             │
│                                                            │
│     medicines: [                                         │
│       {                                                  │
│         name: "Paracetamol"                             │
│         dosage: "500mg"                                 │
│         frequency: "2x/day"                             │
│         duration: "3 days"                              │
│       }                                                  │
│     ]                                                    │
│                                                            │
│     tests: [                                             │
│       {                                                  │
│         test_name: "Blood Test"                         │
│         results: "Normal"                               │
│         document_url: "gs://bucket/test.pdf"            │
│       }                                                  │
│     ]                                                    │
│                                                            │
│     source_document_url: "gs://bucket/prescription.jpg"  │
│     extraction_confidence: 0.95                          │
│   }                                                       │
│ ]                                                         │
│                                                            │
│ active_medications: [                                    │
│   {                                                      │
│     medicine_name: "Amlodipine"                         │
│     dosage: "5mg"                                       │
│     frequency: "1x/day"                                 │
│     prescribed_by_clinic: "CLINIC_001"                 │
│     prescribed_date: ISODate                           │
│     is_active: true                                    │
│   }                                                      │
│ ]                                                         │
│                                                            │
│ created_at: ISODate                                      │
│ updated_at: ISODate                                      │
└────────────────────────────────────────────────────────────┘


SESSIONS Collection:
┌────────────────────────────────────────┐
│ session_token: "jwt_token"             │
│ user_type: "doctor" | "patient"        │
│ user_id: "DOC_001" | "+91-9876543210"  │
│ clinic_id: "CLINIC_001"                │
│ doctor_id: "DOC_001"                   │
│ ip_address: "192.168.1.1"              │
│ user_agent: "Mozilla/5.0..."           │
│ created_at: ISODate                    │
│ expires_at: ISODate                    │
│ is_active: true                        │
└────────────────────────────────────────┘
```

---

## 6. API Endpoint Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    API ENDPOINTS OVERVIEW                       │
└─────────────────────────────────────────────────────────────────┘

AUTHENTICATION ENDPOINTS:
┌─────────────────────────────────────────────────────────────┐
│ POST /api/auth/clinic-login                                 │
│   Input: {clinic_id, doctor_id, password}                   │
│   Output: {token, doctor_info, clinic_info}                 │
│                                                              │
│ POST /api/auth/patient-send-otp                             │
│   Input: {mobile_number}                                    │
│   Output: {message, otp_expiry_seconds}                     │
│                                                              │
│ POST /api/auth/patient-verify-otp                           │
│   Input: {mobile_number, otp}                               │
│   Output: {token, patient_info}                             │
│                                                              │
│ POST /api/auth/logout                                       │
│   Input: {token}                                            │
│   Output: {message}                                         │
└─────────────────────────────────────────────────────────────┘

PATIENT MANAGEMENT ENDPOINTS:
┌─────────────────────────────────────────────────────────────┐
│ GET /api/clinic/search-patient                              │
│   Input: {mobile_number, token}                             │
│   Output: {status, patient_data}                            │
│                                                              │
│ POST /api/clinic/request-patient-access                     │
│   Input: {mobile_number, token}                             │
│   Output: {message}                                         │
│                                                              │
│ POST /api/patient/authorize-clinic-access                   │
│   Input: {mobile_number, clinic_id, otp}                    │
│   Output: {message}                                         │
│                                                              │
│ POST /api/clinic/register-new-patient                       │
│   Input: {mobile_number, name, age, gender, allergies, ...} │
│   Output: {patient_id, message}                             │
│                                                              │
│ GET /api/patient/health-timeline                            │
│   Input: {mobile_number, token}                             │
│   Output: {visits, labs, medications}                       │
└─────────────────────────────────────────────────────────────┘

DOCUMENT & EXTRACTION ENDPOINTS:
┌─────────────────────────────────────────────────────────────┐
│ POST /api/clinic/upload-document                            │
│   Input: {file, mobile_number, token}                       │
│   Output: {document_id, extraction_status}                  │
│                                                              │
│ POST /api/clinic/extract-document                           │
│   Input: {document_id, mobile_number, token}                │
│   Output: {extracted_data, alerts}                          │
│                                                              │
│ GET /api/clinic/patient-history                             │
│   Input: {mobile_number, token}                             │
│   Output: {visits, medicines, allergies, conditions}        │
└─────────────────────────────────────────────────────────────┘

CHATBOT ENDPOINT:
┌─────────────────────────────────────────────────────────────┐
│ POST /api/clinic/chat                                       │
│   Input: {query, mobile_number, token}                      │
│   Output: {answer}                                          │
│                                                              │
│   Example queries:                                          │
│   - "What allergies does this patient have?"                │
│   - "What medicines is the patient on?"                     │
│   - "Show me all visits in the last 3 months"               │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Screen Layout Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLINIC DASHBOARD LAYOUT                      │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ HEADER                                                           │
│ "Upload & extract document"  │  ⚠️ Alert Badge  MongoDB Connected│
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│ ZONE 1: PATIENT SEARCH      │  ZONE 2: UPLOAD & EXTRACT        │
│ ┌──────────────────────────┐ │ ┌──────────────────────────────┐│
│ │ Search by Mobile:        │ │ │ Drop Zone                    ││
│ │ [+91-98765-43210]        │ │ │ [📄 Drop here]               ││
│ │ [SEARCH]                 │ │ │                              ││
│ │                          │ │ │ [EXTRACT & SAVE]             ││
│ │ ┌────────────────────┐   │ │ │                              ││
│ │ │ Patient Card       │   │ │ │ Ask Anything:                ││
│ │ │ ✓ Ramesh Gupta     │   │ │ │ [Show all patients on...]    ││
│ │ │ ✓ Age: 45          │   │ │ │ [→]                          ││
│ │ │ ✓ Allergies: Pen.. │   │ │ │                              ││
│ │ │ ✓ Authorized       │   │ │ │ Recent Patients:             ││
│ │ │                    │   │ │ │ • Ramesh Gupta              ││
│ │ │ [ADD NEW VISIT]    │   │ │ │ • Priya Sharma              ││
│ │ └────────────────────┘   │ │ └──────────────────────────────┘│
│ │                          │ │                                  │
│ └──────────────────────────┘ │ ZONE 3: ALERT SYSTEM            │
│                              │ ┌──────────────────────────────┐│
│                              │ │ ⚠️ CRITICAL ALERT            ││
│                              │ │                              ││
│                              │ │ ALLERGY CONFLICT:            ││
│                              │ │ Patient allergic to          ││
│                              │ │ Penicillin. New prescription ││
│                              │ │ includes Amoxicillin.        ││
│                              │ │                              ││
│                              │ │ [I ACKNOWLEDGE] [CANCEL]     ││
│                              │ └──────────────────────────────┘│
│                              │                                  │
│                              │ CHATBOT SIDEBAR                  │
│                              │ ┌──────────────────────────────┐│
│                              │ │ CliniqAI Assistant           ││
│                              │ │                              ││
│                              │ │ [Chat messages here]         ││
│                              │ │                              ││
│                              │ │ [Input field]                ││
│                              │ │ [Quick: Allergies]           ││
│                              │ └──────────────────────────────┘│
│                                                                  │
└──────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                   PATIENT DASHBOARD LAYOUT                      │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ HEADER                                                           │
│ "My Health Records" | +91-98765-43210  │  [LOGOUT]             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│ MY HEALTH SUMMARY                                                │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ Ramesh Gupta | Age: 45 | Gender: Male                     │  │
│ │ Known Allergies: Penicillin, Aspirin                       │  │
│ │ Chronic Conditions: Diabetes, Hypertension                │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│ HEALTH TIMELINE (Social Media Style)                             │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ 12 Oct 2025 | Dr. Sharma's Clinic                         │  │
│ │ Diagnosis: Viral Fever                                    │  │
│ │ Medicines: Paracetamol 500mg (2x/day)                     │  │
│ │ [VIEW DETAILS] [DOWNLOAD]                                 │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ 05 Oct 2025 | City Hospital                               │  │
│ │ Blood Test - All values normal                            │  │
│ │ [VIEW FULL REPORT] [DOWNLOAD]                             │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│ MY ACTIVE MEDICATIONS                                            │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ Amlodipine 5mg (1x/day) - Prescribed by Dr. Sharma        │  │
│ │ Metformin 500mg (2x/day) - Prescribed by Dr. Patel        │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 8. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    COMPLETE DATA FLOW                           │
└─────────────────────────────────────────────────────────────────┘

DOCTOR UPLOADS PRESCRIPTION:
┌──────────────┐
│ Doctor       │
│ Uploads JPG  │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────┐
│ Frontend (HTML + JS)                     │
│ • File validation                        │
│ • Preview image                          │
│ • Send to backend                        │
└──────┬───────────────────────────────────┘
       │ POST /api/clinic/upload-document
       │ {file, mobile_number, clinic_id, token}
       ▼
┌──────────────────────────────────────────┐
│ FastAPI Backend                          │
│ • Validate token                         │
│ • Check authorization                    │
│ • Store file in Cloud Storage            │
│ • Return document_id                     │
└──────┬───────────────────────────────────┘
       │ document_id
       ▼
┌──────────────────────────────────────────┐
│ Cloud Storage                            │
│ gs://bucket/prescription_001.jpg         │
└──────────────────────────────────────────┘


GEMINI EXTRACTS DATA:
┌──────────────┐
│ Backend      │
│ Calls Gemini │
└──────┬───────┘
       │ POST /api/clinic/extract-document
       │ {document_id, mobile_number, token}
       ▼
┌──────────────────────────────────────────┐
│ Gemini on Vertex AI                      │
│ • Read image from Cloud Storage          │
│ • Extract text (OCR)                     │
│ • Parse structured data                  │
│ • Return JSON                            │
└──────┬───────────────────────────────────┘
       │ {patient_name, medicines, diagnosis, ...}
       ▼
┌──────────────────────────────────────────┐
│ Alert Tool                               │
│ • Get patient history from MongoDB       │
│ • Check allergies                        │
│ • Check drug interactions                │
│ • Generate alerts                        │
└──────┬───────────────────────────────────┘
       │ {alerts: [{severity, message}]}
       ▼
┌──────────────────────────────────────────┐
│ MongoDB                                  │
│ • Store visit record                     │
│ • Update active medications              │
│ • Update patient profile                 │
└──────┬───────────────────────────────────┘
       │ {success: true}
       ▼
┌──────────────────────────────────────────┐
│ Frontend                                 │
│ • Display extracted data                 │
│ • Show alerts (RED/YELLOW/GREEN)         │
│ • Doctor reviews and confirms            │
└──────────────────────────────────────────┘
```

---

## 9. Security Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SECURITY LAYERS                              │
└─────────────────────────────────────────────────────────────────┘

LAYER 1: AUTHENTICATION
┌──────────────────────────────────────────┐
│ Clinic: 3-Factor (Clinic ID + Doc ID + Pwd)
│ Patient: OTP-Based (Mobile + SMS)        │
│ Tokens: JWT (24h clinic, 30d patient)    │
│ Password: bcrypt (10 rounds)              │
└──────────────────────────────────────────┘

LAYER 2: AUTHORIZATION
┌──────────────────────────────────────────┐
│ Patient must authorize clinic access     │
│ OTP-based authorization (SMS)            │
│ Clinic cannot access unauthorized data   │
│ Patient can revoke access anytime        │
└──────────────────────────────────────────┘

LAYER 3: DATA PROTECTION
┌──────────────────────────────────────────┐
│ HTTPS only (no HTTP)                     │
│ Sensitive fields encrypted at rest       │
│ No sensitive data in logs                │
│ Audit log all access attempts            │
└──────────────────────────────────────────┘

LAYER 4: RATE LIMITING
┌──────────────────────────────────────────┐
│ OTP: Max 3 requests per 15 minutes       │
│ OTP verification: Max 3 attempts         │
│ Login: Max 5 attempts per 15 minutes     │
│ API: Rate limit per IP/user              │
└──────────────────────────────────────────┘

LAYER 5: AUDIT TRAIL
┌──────────────────────────────────────────┐
│ Who: Doctor ID + Clinic ID               │
│ What: Action (upload, search, view)      │
│ When: Timestamp                          │
│ Where: IP address                        │
│ Result: Success/Failure                  │
└──────────────────────────────────────────┘
```

---

This visual guide provides a complete overview of Phase 2 architecture, flows, and design.

For detailed implementation, refer to:
- PHASE_2_HIE_IMPLEMENTATION.md
- PHASE_2_UPDATED_BUILD_PLAN.md
- IMPLEMENTATION_STRATEGY.md
