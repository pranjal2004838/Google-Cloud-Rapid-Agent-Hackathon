# PHASE 2: Updated Build Plan - Dual-Platform HIE with Authentication

This document replaces the original Phase 2 section in `CliniqAI_Complete_Build_Plan.md` with the new Dual-Platform Architecture.

---

## Overview: From Clinic Tool to Health Information Exchange

**Original Vision:** Single clinic dashboard for doctors to upload prescriptions and extract data.

**New Vision:** Centralized AI Health Information Exchange (HIE) aligned with India's Ayushman Bharat Digital Mission (ABHA).

**The Game-Changer:**
- Patient's mobile number = Universal identifier across ALL clinics
- Clinic Y can access Clinic X's data about the same patient (with patient authorization)
- **Gemini AI checks for drug conflicts across ALL clinics in real-time**
- **Clinic Y saves a patient's life by catching an allergy from Clinic X 3 months ago**

---

## Authentication & Authorization Architecture

### 1. Three-Factor Clinic Login

**Why 3 factors?**
- Clinic ID: Identifies the healthcare facility
- Doctor ID: Identifies the individual doctor (audit trail)
- Password: Authenticates the doctor

This creates a complete audit trail: "Dr. Sharma at Dr. Sharma's Clinic added patient Ramesh Gupta on 2026-05-20 at 10:30 AM"

```
CLINIC LOGIN SCREEN
┌─────────────────────────────────────┐
│ CliniqAI - Healthcare Provider      │
│                                     │
│ Clinic ID:   [CLINIC_001________]   │
│ Doctor ID:   [DOC_001__________]    │
│ Password:    [**************]       │
│                                     │
│ [LOGIN]  [REGISTER CLINIC]          │
│                                     │
│ Clinic ID format: CLINIC_XXX        │
│ Doctor ID format: DOC_XXX           │
│                                     │
└─────────────────────────────────────┘
```

**Backend Flow:**
```python
POST /api/auth/clinic-login
{
  "clinic_id": "CLINIC_001",
  "doctor_id": "DOC_001",
  "password": "secure_password"
}

VALIDATION:
1. Find clinic in clinics collection by clinic_id
2. Find doctor in clinic.doctors array by doctor_id
3. Verify password_hash using bcrypt
4. Check if doctor.is_active == true
5. Generate JWT token (24-hour expiry)
6. Create session record
7. Return {token, doctor_info, clinic_info}

RESPONSE:
{
  "token": "eyJhbGc...",
  "doctor": {
    "doctor_id": "DOC_001",
    "doctor_name": "Dr. Sharma",
    "department": "General Physician"
  },
  "clinic": {
    "clinic_id": "CLINIC_001",
    "clinic_name": "Dr. Sharma's Clinic",
    "clinic_address": "Mumbai, India"
  }
}
```

---

### 2. OTP-Based Patient Login

**Why OTP?**
- No password to remember
- ABHA-aligned (SMS-based verification)
- More secure for mobile-first users
- Easier for non-tech-savvy patients

```
PATIENT LOGIN SCREEN (Step 1)
┌─────────────────────────────────────┐
│ CliniqAI - My Health Records        │
│                                     │
│ Enter your mobile number:           │
│ [+91-98765-43210____________]       │
│                                     │
│ [SEND OTP]  [BACK]                  │
│                                     │
│ We'll send a 6-digit code to your   │
│ phone for verification.             │
│                                     │
└─────────────────────────────────────┘
         |
         | POST /api/auth/patient-send-otp
         | {mobile_number: "+91-98765-43210"}
         |
         ▼
BACKEND GENERATES OTP:
1. Find patient by mobile_number
   - If not found: Create new patient record
2. Generate 6-digit OTP (random)
3. Store in DB: {mobile, otp, otp_expiry: NOW + 5 min}
4. Send SMS via Twilio/AWS SNS:
   "Your CliniqAI verification code is: 654321"
5. Return {message: "OTP sent", otp_expiry: "5 minutes"}
         |
         ▼
PATIENT OTP VERIFICATION SCREEN (Step 2)
┌─────────────────────────────────────┐
│ Enter OTP sent to +91-98765-43210   │
│                                     │
│ [____] [____] [____] [____] [____]  │
│  [____]                             │
│                                     │
│ [VERIFY & LOGIN]  [RESEND OTP]      │
│                                     │
│ Code expires in: 4:32               │
│                                     │
└─────────────────────────────────────┘
         |
         | POST /api/auth/patient-verify-otp
         | {mobile_number, otp}
         |
         ▼
BACKEND VERIFIES OTP:
1. Find patient by mobile_number
2. Check if OTP matches
3. Check if OTP not expired
4. Mark patient.otp_verified = true
5. Generate JWT token (30-day expiry)
6. Create session record
7. Return {token, patient_info}

RESPONSE:
{
  "token": "eyJhbGc...",
  "patient": {
    "mobile_number": "+91-98765-43210",
    "patient_name": "Ramesh Gupta",
    "age": 45,
    "gender": "Male",
    "known_allergies": ["penicillin", "aspirin"],
    "chronic_conditions": ["diabetes", "hypertension"]
  }
}
```

---

### 3. Cross-Clinic Access Control (OTP-Based Authorization)

**The Critical Flow: Patient moves from Clinic X to Clinic Y**

```
SCENARIO: Doctor at Clinic Y wants to access patient's history from Clinic X

STEP 1: Doctor searches for patient
┌─────────────────────────────────────┐
│ CLINIC DASHBOARD                    │
│                                     │
│ Search Patient by Mobile Number:    │
│ [+91-98765-43210____________]       │
│ [SEARCH]                            │
│                                     │
└─────────────────────────────────────┘
         |
         | POST /api/clinic/search-patient
         | {
         |   mobile_number: "+91-98765-43210",
         |   clinic_id: "CLINIC_002",
         |   doctor_id: "DOC_002",
         |   token: "jwt_token"
         | }
         |
         ▼
BACKEND SEARCH LOGIC:
1. Validate JWT token
2. Find patient by mobile_number
3. Check if patient exists
   - If NO: Return {status: "not_found"}
   - If YES: Continue to step 4
4. Check if clinic_id in patient.authorized_clinics
   - If YES: Return full patient record (CASE A)
   - If NO: Return {status: "not_authorized"} (CASE B)
         |
         ├─────────────────────────────────────┐
         |                                     |
         ▼ CASE A                              ▼ CASE B
    PATIENT FOUND &                    PATIENT FOUND BUT
    AUTHORIZED                         NOT AUTHORIZED
         |                                     |
         |                                     ▼
         |                          ┌──────────────────────────┐
         |                          │ AUTHORIZATION ALERT      │
         |                          │                          │
         |                          │ ⚠️ This patient is not   │
         |                          │ registered at your clinic│
         |                          │                          │
         |                          │ To access their records: │
         |                          │ 1. Patient authorizes    │
         |                          │    via OTP               │
         |                          │ 2. You can then view     │
         |                          │    their history         │
         |                          │                          │
         |                          │ [SEND AUTH OTP]          │
         |                          └──────────────────────────┘
         |                                     |
         |                                     | POST /api/clinic/request-patient-access
         |                                     | {
         |                                     |   mobile_number,
         |                                     |   clinic_id,
         |                                     |   doctor_id
         |                                     | }
         |                                     |
         |                                     ▼
         |                          BACKEND SENDS AUTH OTP:
         |                          1. Generate unique auth_token
         |                          2. Generate OTP (different from login OTP)
         |                          3. Store: {mobile, clinic_id, otp, token}
         |                          4. Send SMS:
         |                             "Dr. Sharma's Clinic requests access
         |                              to your health records.
         |                              Reply with OTP: 654321 to allow"
         |                          5. Return "OTP sent to patient"
         |                                     |
         |                                     ▼
         |                          PATIENT RECEIVES SMS & AUTHORIZES:
         |                          Option A: Reply to SMS with OTP
         |                          Option B: Open app and verify OTP
         |                                     |
         |                                     | POST /api/patient/authorize-clinic-access
         |                                     | {
         |                                     |   mobile_number,
         |                                     |   clinic_id,
         |                                     |   otp
         |                                     | }
         |                                     |
         |                                     ▼
         |                          BACKEND GRANTS ACCESS:
         |                          1. Find patient by mobile_number
         |                          2. Verify OTP matches
         |                          3. Add to authorized_clinics:
         |                             {
         |                               clinic_id: "CLINIC_002",
         |                               clinic_name: "City Hospital",
         |                               access_granted_date: NOW,
         |                               access_status: "active",
         |                               otp_verified: true
         |                             }
         |                          4. Return "Access granted"
         |                                     |
         |                                     ▼
         |                          CLINIC DASHBOARD UPDATES:
         |                          ✓ Patient record now visible
         |                          ✓ Full history from all clinics
         |                          ✓ Can add new visit
         |
         ▼
PATIENT CARD DISPLAYED
┌──────────────────────────────────────┐
│ ✓ Ramesh Gupta                       │
│   Age: 45 | Gender: Male             │
│   Mobile: +91-98765-43210            │
│   Blood Group: O+                    │
│                                      │
│ Known Allergies: Penicillin, Aspirin │
│ Chronic Conditions: Diabetes, HTN    │
│                                      │
│ VISIT HISTORY (All Clinics):         │
│ • 2026-05-20 | Dr. Sharma's Clinic   │
│   Fever | Paracetamol, Cough Syrup   │
│                                      │
│ • 2026-05-10 | City Hospital         │
│   Hypertension | Amlodipine          │
│                                      │
│ • 2026-04-15 | Apollo Hospital       │
│   Diabetes Check | Metformin         │
│                                      │
│ [ADD NEW VISIT] [UPLOAD PRESCRIPTION]│
│                                      │
└──────────────────────────────────────┘
```

---

## Clinic Dashboard: Three Zones

### Zone 1: Patient Search & Onboarding

**Three Cases:**

**Case A: Patient Found & Authorized**
- Show full patient card with history
- Show "Authorized" badge
- Allow adding new visit

**Case B: Patient Found but NOT Authorized**
- Show authorization alert
- Button: "SEND AUTHORIZATION OTP TO PATIENT"
- Patient receives SMS and authorizes
- Once authorized, Case A applies

**Case C: Patient NOT Found (New Patient)**
- Show registration form
- Fields: Mobile, Name, Age, Gender, Blood Group, Allergies
- After registration, patient is added to CliniqAI network
- Doctor can immediately add first visit

### Zone 2: Upload & AI Extraction

- Drop zone for documents (JPG, PNG, PDF)
- File preview
- "EXTRACT & SAVE TO RECORDS" button
- Progress indicator during extraction
- Gemini extracts: medicines, diagnosis, tests, doctor name, date

### Zone 3: Cross-Clinic Alert System

**Three Alert Levels:**

**RED ALERT (HIGH SEVERITY):**
- Allergy conflict
- Dangerous drug-drug interaction
- Requires doctor acknowledgement
- Button: "I ACKNOWLEDGE THIS RISK" or "CANCEL PRESCRIPTION"

**YELLOW ALERT (MEDIUM SEVERITY):**
- Cross-allergy warning
- Moderate drug-drug interaction
- Informational, doesn't block

**GREEN OK (NO ALERTS):**
- "No drug conflicts detected"
- Safe to proceed

---

## Patient Dashboard: Three Zones

### Zone 1: My Health Timeline

Social media-style feed of visits across all clinics:
- Date
- Clinic name & doctor
- Diagnosis
- Medicines prescribed
- Tests ordered
- View full details button
- Download prescription button

### Zone 2: My Active Medications

Consolidated list of all current medicines across all clinics:
- Medicine name
- Dosage
- Frequency
- Prescribed by (clinic + doctor)
- Prescribed date

### Zone 3: My Allergies & Conditions

- Known allergies (prominently displayed)
- Chronic conditions
- Blood group
- Note: "Doctors are alerted if they try to prescribe related medicines"

---

## Database Schema (MongoDB)

### CLINICS Collection

```javascript
{
  _id: ObjectId,
  clinic_id: "CLINIC_001",
  clinic_name: "Dr. Sharma's Clinic",
  clinic_email: "clinic@example.com",
  clinic_phone: "+91-9876543210",
  clinic_address: "Mumbai, India",
  clinic_password_hash: "bcrypt_hash",
  clinic_registration_date: ISODate,
  clinic_status: "active",
  
  doctors: [
    {
      doctor_id: "DOC_001",
      doctor_name: "Dr. Sharma",
      doctor_email: "sharma@clinic.com",
      department: "General Physician",
      password_hash: "bcrypt_hash",
      is_active: true,
      created_at: ISODate,
      last_login: ISODate
    }
  ],
  
  created_at: ISODate,
  updated_at: ISODate
}
```

### PATIENTS Collection (Mobile Number as Primary Key)

```javascript
{
  _id: ObjectId,
  mobile_number: "+91-9876543210",  // UNIQUE - Universal ABHA ID
  patient_name: "Ramesh Gupta",
  age: 45,
  gender: "Male",
  email: "patient@example.com",
  blood_group: "O+",
  
  // Authentication
  otp: "123456",
  otp_expiry: ISODate,
  otp_verified: true,
  
  // Health Profile
  known_allergies: ["penicillin", "aspirin"],
  chronic_conditions: ["diabetes", "hypertension"],
  
  // Cross-Clinic Authorization
  authorized_clinics: [
    {
      clinic_id: "CLINIC_001",
      clinic_name: "Dr. Sharma's Clinic",
      access_granted_date: ISODate,
      access_status: "active",
      otp_verified: true
    }
  ],
  
  // Complete Visit History
  visits: [
    {
      visit_id: ObjectId,
      clinic_id: "CLINIC_001",
      clinic_name: "Dr. Sharma's Clinic",
      doctor_id: "DOC_001",
      doctor_name: "Dr. Sharma",
      visit_date: ISODate,
      diagnosis: "Viral Fever",
      symptoms: ["fever", "cough"],
      
      medicines: [
        {
          name: "Paracetamol",
          dosage: "500mg",
          frequency: "2x/day",
          duration: "3 days",
          prescribed_date: ISODate
        }
      ],
      
      tests: [
        {
          test_name: "Blood Test",
          test_date: ISODate,
          results: "Normal",
          document_url: "gs://bucket/test_001.pdf"
        }
      ],
      
      source_document_url: "gs://bucket/prescription_001.jpg",
      extraction_confidence: 0.95,
      notes: "Patient advised rest and fluids",
      created_at: ISODate
    }
  ],
  
  // Current Active Medications
  active_medications: [
    {
      medicine_name: "Amlodipine",
      dosage: "5mg",
      frequency: "1x/day",
      prescribed_by_clinic: "CLINIC_001",
      prescribed_date: ISODate,
      is_active: true
    }
  ],
  
  created_at: ISODate,
  updated_at: ISODate
}
```

### SESSIONS Collection

```javascript
{
  _id: ObjectId,
  session_token: "jwt_token",
  user_type: "clinic" | "doctor" | "patient",
  user_id: "CLINIC_001" | "DOC_001" | "+91-9876543210",
  clinic_id: "CLINIC_001",
  doctor_id: "DOC_001",
  ip_address: "192.168.1.1",
  user_agent: "Mozilla/5.0...",
  created_at: ISODate,
  expires_at: ISODate,
  is_active: true
}
```

---

## Backend API Endpoints

### Authentication

```
POST /api/auth/clinic-login
  Input: {clinic_id, doctor_id, password}
  Output: {token, doctor_info, clinic_info}

POST /api/auth/patient-send-otp
  Input: {mobile_number}
  Output: {message, otp_expiry}

POST /api/auth/patient-verify-otp
  Input: {mobile_number, otp}
  Output: {token, patient_info}

POST /api/auth/logout
  Input: {token}
  Output: {message}
```

### Patient Management

```
GET /api/clinic/search-patient
  Input: {mobile_number, clinic_id, doctor_id, token}
  Output: {patient_data} or {status: "not_authorized"}

POST /api/clinic/request-patient-access
  Input: {mobile_number, clinic_id, doctor_id, token}
  Output: {message: "OTP sent to patient"}

POST /api/patient/authorize-clinic-access
  Input: {mobile_number, clinic_id, otp}
  Output: {message: "Access granted"}

POST /api/clinic/register-new-patient
  Input: {mobile_number, name, age, gender, blood_group, allergies, token}
  Output: {patient_id, message}

GET /api/patient/health-timeline
  Input: {mobile_number, token}
  Output: {visits, labs, medications}
```

### Document & Extraction

```
POST /api/clinic/upload-document
  Input: {file, mobile_number, clinic_id, doctor_id, token}
  Output: {document_id, extraction_status}

POST /api/clinic/extract-document
  Input: {document_id, mobile_number, token}
  Output: {extracted_data, alerts}

GET /api/clinic/patient-history
  Input: {mobile_number, clinic_id, token}
  Output: {visits, medicines, allergies, conditions}
```

---

## Chatbot Integration (Clinic Dashboard Sidebar)

**Chatbot Features:**
- Ask about patient allergies
- Ask about patient medications
- Ask about patient visit history
- Ask about drug interactions
- Natural language queries

**Example Queries:**
```
"What allergies does this patient have?"
→ "Penicillin (since 2025-10-12), Aspirin (since 2025-09-05)"

"What medicines is the patient currently on?"
→ "Amlodipine 5mg (1x/day), Metformin 500mg (2x/day)"

"Show me all visits in the last 3 months"
→ "3 visits: Fever (May 20), Hypertension check (May 10), Diabetes review (Apr 15)"

"Is there any interaction between Amlodipine and Simvastatin?"
→ "YES - MEDIUM severity. Simvastatin dose should not exceed 20mg with Amlodipine."
```

---

## Implementation Roadmap

### Week 1: Authentication & Database
- [ ] Design MongoDB schema
- [ ] Implement clinic login (3-factor)
- [ ] Implement patient OTP login
- [ ] Implement cross-clinic authorization
- [ ] JWT token generation & validation

### Week 2: Clinic Dashboard UI
- [ ] Patient search zone
- [ ] New patient registration
- [ ] Document upload zone
- [ ] Alert system (red/yellow/green)
- [ ] API integration

### Week 3: Patient Dashboard UI
- [ ] Health timeline
- [ ] Active medications
- [ ] Allergies & conditions
- [ ] Lab reports & scans
- [ ] Read-only access control

### Week 4: Chatbot & Polish
- [ ] Chatbot sidebar
- [ ] Natural language queries
- [ ] Testing & bug fixes
- [ ] Demo preparation

---

## Security Checklist

- [ ] Passwords hashed with bcrypt (min 10 rounds)
- [ ] OTP: 6-digit, 5-minute expiry
- [ ] OTP rate limiting: Max 3 requests per 15 min
- [ ] JWT tokens: 24-hour (clinic), 30-day (patient)
- [ ] HTTPS only for all API calls
- [ ] Patient must authorize clinic access via OTP
- [ ] Audit log all access attempts
- [ ] Encrypt sensitive fields at rest
- [ ] No sensitive data in logs

---

## Demo Script for Judges

```
SCENE 1: Clinic Login
- Doctor logs in with Clinic ID + Doctor ID + Password
- Dashboard loads

SCENE 2: Patient Search (New Clinic)
- Doctor enters patient's mobile number
- System shows "Patient not authorized"
- Doctor sends authorization OTP
- (Simulate) Patient authorizes via SMS
- Patient's complete history appears

SCENE 3: Cross-Clinic Alert (THE WOW MOMENT)
- Doctor uploads new prescription
- Gemini extracts: Amoxicillin
- RED ALERT: "Patient allergic to Penicillin since Oct 2025 at Apollo Hospital"
- Alert: "Amoxicillin is penicillin-based antibiotic"
- Doctor acknowledges and cancels

SCENE 4: Patient Portal
- Switch to patient view
- Show health timeline from multiple clinics
- Show consolidated medications
- Show allergies prominently

JUDGES' TAKEAWAY:
"This is a health information exchange that could prevent patient deaths
by catching drug conflicts across clinics."
```

---

## Key Differentiators

1. **ABHA-Aligned:** Mobile number as universal identifier
2. **Cross-Clinic Intelligence:** Gemini checks conflicts across ALL clinics
3. **Patient Control:** OTP-based authorization prevents unauthorized access
4. **Audit Trail:** 3-factor clinic login (clinic + doctor + password)
5. **Real-Time Alerts:** Red alert box is unmissable
6. **Dual Portals:** Separate UX for providers and patients

This is not just a clinic tool. This is a health information exchange that could save lives.
