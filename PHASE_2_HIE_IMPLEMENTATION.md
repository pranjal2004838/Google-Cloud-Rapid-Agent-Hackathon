# PHASE 2: Dual-Platform HIE Implementation Guide
## CliniqAI as Centralized Health Information Exchange (ABHA-Aligned)

---

## 1. AUTHENTICATION & AUTHORIZATION ARCHITECTURE

### 1.1 Database Schema for Auth

```javascript
// MongoDB Collections

// CLINICS Collection
{
  _id: ObjectId,
  clinic_id: "CLINIC_001",           // Unique clinic identifier
  clinic_name: "Dr. Sharma's Clinic",
  clinic_email: "clinic@example.com",
  clinic_phone: "+91-9876543210",
  clinic_address: "Mumbai, India",
  clinic_password_hash: "bcrypt_hash",
  clinic_registration_date: ISODate,
  clinic_status: "active" | "inactive" | "suspended",
  
  // Doctors working at this clinic
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

// PATIENTS Collection (Mobile Number as Primary Key)
{
  _id: ObjectId,
  mobile_number: "+91-9876543210",    // UNIQUE - Universal identifier (ABHA-aligned)
  patient_name: "Ramesh Gupta",
  age: 45,
  gender: "Male",
  email: "patient@example.com",
  
  // OTP for patient login
  otp: "123456",
  otp_expiry: ISODate,
  otp_verified: true,
  
  // Patient's health profile
  known_allergies: ["penicillin", "aspirin"],
  chronic_conditions: ["diabetes", "hypertension"],
  blood_group: "O+",
  
  // Which clinics have access to this patient's record?
  // This is the KEY for cross-clinic authorization
  authorized_clinics: [
    {
      clinic_id: "CLINIC_001",
      clinic_name: "Dr. Sharma's Clinic",
      access_granted_date: ISODate,
      access_status: "active" | "revoked",
      otp_verified: true,  // Patient gave OTP to grant access
      access_level: "full" | "limited"
    }
  ],
  
  // Complete visit history across ALL clinics
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
      
      // Medicines prescribed at THIS visit
      medicines: [
        {
          name: "Paracetamol",
          dosage: "500mg",
          frequency: "2x/day",
          duration: "3 days",
          prescribed_date: ISODate
        }
      ],
      
      // Tests ordered at THIS visit
      tests: [
        {
          test_name: "Blood Test",
          test_date: ISODate,
          results: "Normal",
          document_url: "gs://bucket/test_001.pdf"
        }
      ],
      
      // Original uploaded document
      source_document_url: "gs://bucket/prescription_001.jpg",
      extracted_by_gemini: true,
      extraction_confidence: 0.95,
      
      notes: "Patient advised rest and fluids",
      created_at: ISODate,
      updated_at: ISODate
    }
  ],
  
  // Current active medications (consolidated across all clinics)
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

// SESSIONS Collection (for tracking active logins)
{
  _id: ObjectId,
  session_token: "jwt_token_here",
  user_type: "clinic" | "doctor" | "patient",
  user_id: "CLINIC_001" | "DOC_001" | "+91-9876543210",
  clinic_id: "CLINIC_001",  // For doctor sessions
  doctor_id: "DOC_001",      // For doctor sessions
  ip_address: "192.168.1.1",
  user_agent: "Mozilla/5.0...",
  created_at: ISODate,
  expires_at: ISODate,
  is_active: true
}
```

---

## 2. AUTHENTICATION FLOWS

### 2.1 Clinic Login Flow

```
┌─────────────────────────────────────────────────────┐
│ CLINIC LOGIN SCREEN                                 │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Clinic ID:    [CLINIC_001____________]             │
│ Doctor ID:    [DOC_001_______________]             │
│ Password:     [********************]               │
│                                                     │
│ [LOGIN]  [REGISTER NEW CLINIC]                     │
│                                                     │
└─────────────────────────────────────────────────────┘
         |
         | POST /api/auth/clinic-login
         | {clinic_id, doctor_id, password}
         |
         ▼
┌─────────────────────────────────────────────────────┐
│ BACKEND VALIDATION                                  │
├─────────────────────────────────────────────────────┤
│ 1. Find clinic by clinic_id                         │
│ 2. Find doctor within clinic.doctors array          │
│ 3. Verify password_hash                             │
│ 4. Check if doctor is_active = true                 │
│ 5. Generate JWT token                               │
│ 6. Create session record                            │
│ 7. Return token + doctor info                       │
└─────────────────────────────────────────────────────┘
         |
         ▼
┌─────────────────────────────────────────────────────┐
│ CLINIC DASHBOARD (Doctor logged in)                 │
├─────────────────────────────────────────────────────┤
│ Header: "Welcome, Dr. Sharma | CLINIC_001"          │
│ [LOGOUT]                                            │
└─────────────────────────────────────────────────────┘
```

### 2.2 Patient Login Flow (OTP-Based)

```
┌─────────────────────────────────────────────────────┐
│ PATIENT LOGIN SCREEN                                │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Mobile Number: [+91-98765-43210_______]            │
│                                                     │
│ [SEND OTP]  [BACK]                                 │
│                                                     │
└─────────────────────────────────────────────────────┘
         |
         | POST /api/auth/patient-send-otp
         | {mobile_number}
         |
         ▼
┌─────────────────────────────────────────────────────┐
│ BACKEND: SEND OTP                                   │
├─────────────────────────────────────────────────────┤
│ 1. Find patient by mobile_number                    │
│ 2. Generate 6-digit OTP                             │
│ 3. Store OTP + expiry (5 min) in DB                 │
│ 4. Send OTP via SMS (Twilio/AWS SNS)                │
│ 5. Return "OTP sent" message                        │
└─────────────────────────────────────────────────────┘
         |
         ▼
┌─────────────────────────────────────────────────────┐
│ PATIENT OTP VERIFICATION SCREEN                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Enter OTP sent to +91-98765-43210:                 │
│ [____] [____] [____] [____] [____] [____]          │
│                                                     │
│ [VERIFY & LOGIN]  [RESEND OTP]                     │
│                                                     │
└─────────────────────────────────────────────────────┘
         |
         | POST /api/auth/patient-verify-otp
         | {mobile_number, otp}
         |
         ▼
┌─────────────────────────────────────────────────────┐
│ BACKEND: VERIFY OTP                                 │
├─────────────────────────────────────────────────────┤
│ 1. Find patient by mobile_number                    │
│ 2. Check if OTP matches and not expired             │
│ 3. Mark otp_verified = true                         │
│ 4. Generate JWT token                               │
│ 5. Create session record                            │
│ 6. Return token + patient info                      │
└─────────────────────────────────────────────────────┘
         |
         ▼
┌─────────────────────────────────────────────────────┐
│ PATIENT DASHBOARD                                   │
├─────────────────────────────────────────────────────┤
│ Header: "My Health Records | +91-98765-43210"       │
│ [LOGOUT]                                            │
└─────────────────────────────────────────────────────┘
```

---

## 3. CROSS-CLINIC ACCESS CONTROL (OTP-Based Authorization)

### Scenario: Patient moves from Clinic X to Clinic Y

```
STEP 1: Doctor at Clinic Y enters patient's mobile number
┌─────────────────────────────────────────────────────┐
│ CLINIC DASHBOARD - PATIENT SEARCH                   │
├─────────────────────────────────────────────────────┤
│ Search Patient by Mobile Number:                    │
│ [+91-98765-43210_______________________]            │
│ [SEARCH]                                            │
└─────────────────────────────────────────────────────┘
         |
         | POST /api/clinic/search-patient
         | {mobile_number, clinic_id, doctor_id}
         |
         ▼
┌─────────────────────────────────────────────────────┐
│ BACKEND: SEARCH PATIENT                             │
├─────────────────────────────────────────────────────┤
│ 1. Find patient by mobile_number                    │
│ 2. Check if current clinic in authorized_clinics   │
│ 3. If YES: Return full patient record               │
│ 4. If NO: Return "Access Denied - Need OTP"         │
└─────────────────────────────────────────────────────┘
         |
         ▼
┌─────────────────────────────────────────────────────┐
│ CASE A: Patient already authorized at this clinic   │
├─────────────────────────────────────────────────────┤
│ ✓ Patient record loaded                             │
│ ✓ Full history visible                              │
│ ✓ Can add new visit                                 │
└─────────────────────────────────────────────────────┘

         OR

┌─────────────────────────────────────────────────────┐
│ CASE B: New clinic - Need patient authorization     │
├─────────────────────────────────────────────────────┤
│ ⚠️  "This patient is not registered at your clinic" │
│                                                     │
│ To access their health records:                     │
│ 1. Patient must authorize this clinic               │
│ 2. Patient will receive OTP on their phone          │
│ 3. Patient enters OTP to grant access               │
│                                                     │
│ [SEND AUTHORIZATION OTP TO PATIENT]                 │
└─────────────────────────────────────────────────────┘
         |
         | POST /api/clinic/request-patient-access
         | {mobile_number, clinic_id, doctor_id}
         |
         ▼
┌─────────────────────────────────────────────────────┐
│ BACKEND: SEND AUTHORIZATION OTP                     │
├─────────────────────────────────────────────────────┤
│ 1. Generate authorization_token (unique)            │
│ 2. Generate OTP (different from login OTP)          │
│ 3. Store in DB: {mobile, clinic_id, otp, token}    │
│ 4. Send SMS: "Dr. Sharma's Clinic requests access  │
│    to your health records. Reply with OTP: 654321" │
│ 5. Return "OTP sent to patient"                     │
└─────────────────────────────────────────────────────┘
         |
         ▼
┌─────────────────────────────────────────────────────┐
│ PATIENT RECEIVES SMS                                │
├─────────────────────────────────────────────────────┤
│ "Dr. Sharma's Clinic requests access to your       │
│  health records. Reply with OTP: 654321 to allow"  │
│                                                     │
│ Patient can:                                        │
│ A) Reply with OTP via SMS (auto-verified)           │
│ B) Open CliniqAI app and verify there               │
└─────────────────────────────────────────────────────┘
         |
         | POST /api/patient/authorize-clinic-access
         | {mobile_number, clinic_id, otp}
         |
         ▼
┌─────────────────────────────────────────────────────┐
│ BACKEND: VERIFY AUTHORIZATION OTP                   │
├─────────────────────────────────────────────────────┤
│ 1. Find patient by mobile_number                    │
│ 2. Verify OTP matches                               │
│ 3. Add clinic to authorized_clinics array:          │
│    {                                                │
│      clinic_id: "CLINIC_002",                       │
│      clinic_name: "City Hospital",                  │
│      access_granted_date: NOW,                      │
│      access_status: "active",                       │
│      otp_verified: true                             │
│    }                                                │
│ 4. Return "Access granted"                          │
└─────────────────────────────────────────────────────┘
         |
         ▼
┌─────────────────────────────────────────────────────┐
│ CLINIC DASHBOARD: Patient Record Now Visible        │
├─────────────────────────────────────────────────────┤
│ ✓ Patient: Ramesh Gupta                             │
│ ✓ Mobile: +91-98765-43210                           │
│ ✓ Age: 45 | Gender: Male                            │
│ ✓ Known Allergies: Penicillin, Aspirin              │
│ ✓ Chronic Conditions: Diabetes, Hypertension        │
│                                                     │
│ VISIT HISTORY (from all clinics):                   │
│ • 2026-05-20 | Dr. Sharma's Clinic | Fever         │
│ • 2026-05-10 | City Hospital | Hypertension        │
│ • 2026-04-15 | Apollo Hospital | Diabetes Check    │
│                                                     │
│ [ADD NEW VISIT] [UPLOAD PRESCRIPTION]               │
└─────────────────────────────────────────────────────┘
```

---

## 4. CLINIC DASHBOARD - DETAILED ZONES

### Zone 1: Patient Search & Onboarding

```html
<!-- PATIENT SEARCH SECTION -->
<div class="patient-search-zone">
  <div class="search-header">
    <h2>Find Patient by Mobile Number</h2>
    <p>Enter patient's mobile to access their centralized health record</p>
  </div>
  
  <div class="search-input-group">
    <input 
      id="patient-mobile" 
      type="tel" 
      placeholder="+91-98765-43210"
      pattern="[0-9\-\+]+"
    />
    <button onclick="searchPatient()">SEARCH</button>
  </div>
  
  <!-- CASE 1: Patient Found & Authorized -->
  <div id="patient-found-authorized" class="hidden">
    <div class="patient-card">
      <div class="patient-header">
        <div class="avatar">RG</div>
        <div class="patient-info">
          <h3>Ramesh Gupta</h3>
          <p>Age: 45 | Gender: Male | Blood Group: O+</p>
          <p class="mobile">+91-98765-43210</p>
        </div>
        <span class="badge-authorized">✓ Authorized</span>
      </div>
      
      <div class="patient-details">
        <div class="detail-row">
          <span class="label">Known Allergies:</span>
          <span class="value allergies">Penicillin, Aspirin</span>
        </div>
        <div class="detail-row">
          <span class="label">Chronic Conditions:</span>
          <span class="value">Diabetes, Hypertension</span>
        </div>
        <div class="detail-row">
          <span class="label">Last Visit:</span>
          <span class="value">2026-05-20 at Dr. Sharma's Clinic</span>
        </div>
      </div>
      
      <div class="action-buttons">
        <button onclick="viewFullHistory()">VIEW FULL HISTORY</button>
        <button onclick="addNewVisit()">ADD NEW VISIT TODAY</button>
      </div>
    </div>
  </div>
  
  <!-- CASE 2: Patient Found but NOT Authorized -->
  <div id="patient-found-unauthorized" class="hidden">
    <div class="authorization-alert">
      <div class="alert-icon">⚠️</div>
      <div class="alert-content">
        <h3>Patient Not Registered at Your Clinic</h3>
        <p>This patient exists in CliniqAI but has not authorized your clinic to access their records.</p>
        <p>To proceed, the patient must authorize your clinic via OTP.</p>
      </div>
      
      <div class="authorization-steps">
        <div class="step">
          <span class="step-number">1</span>
          <span class="step-text">We'll send an OTP to the patient's phone</span>
        </div>
        <div class="step">
          <span class="step-number">2</span>
          <span class="step-text">Patient verifies OTP to grant access</span>
        </div>
        <div class="step">
          <span class="step-number">3</span>
          <span class="step-text">You can then view and add to their record</span>
        </div>
      </div>
      
      <button 
        onclick="sendAuthorizationOTP()" 
        class="btn-primary"
      >
        SEND AUTHORIZATION OTP TO PATIENT
      </button>
    </div>
  </div>
  
  <!-- CASE 3: Patient NOT Found (New Patient) -->
  <div id="patient-not-found" class="hidden">
    <div class="new-patient-form">
      <h3>Register New Patient</h3>
      <p>This patient is not yet in CliniqAI. Register them now.</p>
      
      <form onsubmit="registerNewPatient(event)">
        <div class="form-group">
          <label>Mobile Number (ABHA ID)</label>
          <input type="tel" id="new-patient-mobile" required />
        </div>
        
        <div class="form-group">
          <label>Full Name</label>
          <input type="text" id="new-patient-name" required />
        </div>
        
        <div class="form-group">
          <label>Age</label>
          <input type="number" id="new-patient-age" required />
        </div>
        
        <div class="form-group">
          <label>Gender</label>
          <select id="new-patient-gender" required>
            <option value="">Select...</option>
            <option value="Male">Male</option>
            <option value="Female">Female</option>
            <option value="Other">Other</option>
          </select>
        </div>
        
        <div class="form-group">
          <label>Blood Group (Optional)</label>
          <select id="new-patient-blood-group">
            <option value="">Select...</option>
            <option value="O+">O+</option>
            <option value="O-">O-</option>
            <option value="A+">A+</option>
            <option value="A-">A-</option>
            <option value="B+">B+</option>
            <option value="B-">B-</option>
            <option value="AB+">AB+</option>
            <option value="AB-">AB-</option>
          </select>
        </div>
        
        <div class="form-group">
          <label>Known Allergies (comma-separated)</label>
          <input type="text" id="new-patient-allergies" placeholder="e.g., Penicillin, Aspirin" />
        </div>
        
        <button type="submit" class="btn-primary">REGISTER & PROCEED</button>
      </form>
    </div>
  </div>
</div>
```

### Zone 2: Upload & AI Extraction

```html
<!-- UPLOAD & EXTRACTION SECTION -->
<div class="upload-zone">
  <div class="upload-header">
    <h2>Upload Patient Document</h2>
    <p>Prescription · Lab Report · Discharge Summary · X-Ray · MRI</p>
  </div>
  
  <!-- Drop Zone -->
  <div 
    id="drop-zone" 
    class="drop-zone"
    ondrop="handleDrop(event)"
    ondragover="handleDragOver(event)"
    ondragleave="handleDragLeave(event)"
  >
    <div class="drop-icon">📄</div>
    <div class="drop-text">Drop document here or click to upload</div>
    <div class="drop-hint">JPG · PNG · PDF · Supports handwriting & Hindi text</div>
    <input 
      id="file-input" 
      type="file" 
      accept=".jpg,.jpeg,.png,.pdf"
      onchange="handleFileSelect(event)"
      style="display: none"
    />
  </div>
  
  <!-- File Preview -->
  <div id="file-preview" class="hidden">
    <img id="preview-image" src="" alt="Preview" />
    <button onclick="clearFile()">✕ Clear</button>
  </div>
  
  <!-- Extract Button -->
  <button 
    onclick="extractDocument()" 
    class="btn-extract"
    id="extract-btn"
    disabled
  >
    ⚙️ EXTRACT & SAVE TO RECORDS
  </button>
  
  <!-- Extraction Progress -->
  <div id="extraction-progress" class="hidden">
    <div class="spinner"></div>
    <p>Gemini AI is extracting data...</p>
    <p class="progress-detail">Reading document · Identifying patient · Checking allergies...</p>
  </div>
</div>
```

### Zone 3: Cross-Clinic Alert System

```html
<!-- ALERT SYSTEM SECTION -->
<div class="alert-zone">
  
  <!-- RED ALERT BOX (High Severity) -->
  <div id="alert-box-high" class="hidden alert-box alert-high">
    <div class="alert-header">
      <span class="alert-icon">⚠️ CRITICAL ALERT</span>
      <span class="alert-close" onclick="dismissAlert()">✕</span>
    </div>
    <div class="alert-content">
      <div id="alert-messages-high" class="alert-messages">
        <!-- Dynamically populated -->
        <!-- Example:
        <div class="alert-message">
          <strong>ALLERGY CONFLICT:</strong> Patient was marked allergic to 
          <span class="highlight">Penicillin</span> on 2025-10-12 at 
          <span class="clinic-name">Apollo Hospital</span>. 
          New prescription includes <span class="highlight">Amoxicillin</span> 
          (penicillin-based antibiotic).
        </div>
        -->
      </div>
    </div>
    <div class="alert-footer">
      <button onclick="acknowledgeAlert()" class="btn-acknowledge">
        I ACKNOWLEDGE THIS RISK
      </button>
      <button onclick="cancelPrescription()" class="btn-cancel">
        CANCEL PRESCRIPTION
      </button>
    </div>
  </div>
  
  <!-- YELLOW ALERT BOX (Medium Severity) -->
  <div id="alert-box-medium" class="hidden alert-box alert-medium">
    <div class="alert-header">
      <span class="alert-icon">⚡ WARNING</span>
      <span class="alert-close" onclick="dismissAlert()">✕</span>
    </div>
    <div class="alert-content">
      <div id="alert-messages-medium" class="alert-messages">
        <!-- Dynamically populated -->
      </div>
    </div>
  </div>
  
  <!-- GREEN OK BOX (No Alerts) -->
  <div id="alert-box-ok" class="hidden alert-box alert-ok">
    <div class="alert-content">
      <span class="alert-icon">✓</span>
      <span class="alert-text">No drug conflicts detected. Safe to proceed.</span>
    </div>
  </div>
  
</div>
```

---

## 5. PATIENT DASHBOARD - DETAILED ZONES

### Zone 1: My Health Timeline

```html
<!-- PATIENT HEALTH TIMELINE -->
<div class="patient-timeline">
  <div class="timeline-header">
    <h2>My Health Records</h2>
    <p>Complete history across all clinics</p>
  </div>
  
  <!-- Timeline Cards (Social Media Style) -->
  <div class="timeline-feed">
    
    <!-- Visit Card -->
    <div class="timeline-card visit-card">
      <div class="card-date">12 Oct 2025</div>
      <div class="card-clinic">
        <span class="clinic-name">Dr. Sharma's Clinic</span>
        <span class="doctor-name">Dr. Sharma (General Physician)</span>
      </div>
      
      <div class="card-content">
        <div class="diagnosis">
          <strong>Diagnosis:</strong> Viral Fever
        </div>
        <div class="symptoms">
          <strong>Symptoms:</strong> Fever, Cough, Body Ache
        </div>
      </div>
      
      <div class="card-medicines">
        <strong>Prescribed Medicines:</strong>
        <ul>
          <li>Paracetamol 500mg - 2x/day for 3 days</li>
          <li>Cough Syrup - 1 spoon 3x/day</li>
        </ul>
      </div>
      
      <div class="card-footer">
        <button onclick="viewDetails()">VIEW FULL DETAILS</button>
        <button onclick="downloadPrescription()">📥 DOWNLOAD PRESCRIPTION</button>
      </div>
    </div>
    
    <!-- Lab Report Card -->
    <div class="timeline-card lab-card">
      <div class="card-date">05 Oct 2025</div>
      <div class="card-clinic">
        <span class="clinic-name">City Hospital</span>
        <span class="test-type">Blood Test</span>
      </div>
      
      <div class="card-content">
        <strong>Key Findings (AI Summary):</strong>
        <p>All values normal. Hemoglobin: 14.5 g/dL (Normal). Blood Sugar: 95 mg/dL (Normal).</p>
      </div>
      
      <div class="card-footer">
        <button onclick="viewFullReport()">VIEW FULL REPORT</button>
        <button onclick="downloadReport()">📥 DOWNLOAD PDF</button>
      </div>
    </div>
    
  </div>
</div>
```

### Zone 2: My Active Medications

```html
<!-- ACTIVE MEDICATIONS (Consolidated) -->
<div class="active-medications">
  <div class="section-header">
    <h3>My Current Medicines</h3>
    <p>Consolidated across all your doctors</p>
  </div>
  
  <div class="medications-list">
    <div class="medication-card">
      <div class="med-name">Amlodipine</div>
      <div class="med-details">
        <span class="dosage">5mg</span>
        <span class="frequency">1x/day</span>
        <span class="prescribed-by">Prescribed by Dr. Sharma (2026-05-01)</span>
      </div>
      <div class="med-status active">Active</div>
    </div>
    
    <div class="medication-card">
      <div class="med-name">Metformin</div>
      <div class="med-details">
        <span class="dosage">500mg</span>
        <span class="frequency">2x/day</span>
        <span class="prescribed-by">Prescribed by Dr. Patel (2026-04-15)</span>
      </div>
      <div class="med-status active">Active</div>
    </div>
  </div>
</div>
```

### Zone 3: My Allergies & Conditions

```html
<!-- ALLERGIES & CONDITIONS -->
<div class="allergies-conditions">
  <div class="section-header">
    <h3>My Health Profile</h3>
  </div>
  
  <div class="profile-grid">
    <div class="profile-card allergies">
      <h4>Known Allergies</h4>
      <div class="allergy-list">
        <span class="allergy-badge">Penicillin</span>
        <span class="allergy-badge">Aspirin</span>
      </div>
      <p class="note">⚠️ These are critical. Doctors are alerted if they try to prescribe related medicines.</p>
    </div>
    
    <div class="profile-card conditions">
      <h4>Chronic Conditions</h4>
      <div class="condition-list">
        <span class="condition-badge">Diabetes</span>
        <span class="condition-badge">Hypertension</span>
      </div>
    </div>
    
    <div class="profile-card blood-group">
      <h4>Blood Group</h4>
      <div class="blood-group-display">O+</div>
    </div>
  </div>
</div>
```

---

## 6. BACKEND API ENDPOINTS

### Authentication Endpoints

```python
# POST /api/auth/clinic-login
# Input: {clinic_id, doctor_id, password}
# Output: {token, doctor_info, clinic_info}

# POST /api/auth/patient-send-otp
# Input: {mobile_number}
# Output: {message, otp_expiry}

# POST /api/auth/patient-verify-otp
# Input: {mobile_number, otp}
# Output: {token, patient_info}

# POST /api/auth/logout
# Input: {token}
# Output: {message}
```

### Patient Management Endpoints

```python
# GET /api/clinic/search-patient
# Input: {mobile_number, clinic_id, doctor_id}
# Output: {patient_data} or {error: "Not authorized"}

# POST /api/clinic/request-patient-access
# Input: {mobile_number, clinic_id, doctor_id}
# Output: {message: "OTP sent to patient"}

# POST /api/patient/authorize-clinic-access
# Input: {mobile_number, clinic_id, otp}
# Output: {message: "Access granted"}

# POST /api/clinic/register-new-patient
# Input: {mobile_number, name, age, gender, blood_group, allergies}
# Output: {patient_id, message}

# GET /api/patient/health-timeline
# Input: {mobile_number, token}
# Output: {visits, labs, medications}
```

### Document & Extraction Endpoints

```python
# POST /api/clinic/upload-document
# Input: {file, mobile_number, clinic_id, doctor_id}
# Output: {document_id, extraction_status}

# POST /api/clinic/extract-document
# Input: {document_id, mobile_number}
# Output: {extracted_data, alerts}

# GET /api/clinic/patient-history
# Input: {mobile_number, clinic_id}
# Output: {visits, medicines, allergies, conditions}
```

---

## 7. IMPLEMENTATION ROADMAP (PHASE 2)

### Week 1: Authentication & Authorization
- [ ] Design MongoDB schema for clinics, doctors, patients, sessions
- [ ] Implement clinic login (clinic_id + doctor_id + password)
- [ ] Implement patient OTP login
- [ ] Implement cross-clinic authorization (OTP-based access control)
- [ ] Create JWT token generation & validation

### Week 2: Clinic Dashboard UI
- [ ] Build patient search zone (search by mobile)
- [ ] Build new patient registration form
- [ ] Build document upload zone
- [ ] Build alert system (red/yellow/green boxes)
- [ ] Integrate with backend APIs

### Week 3: Patient Dashboard UI
- [ ] Build health timeline (social media style)
- [ ] Build active medications list
- [ ] Build allergies & conditions display
- [ ] Build lab reports & scans grid
- [ ] Implement read-only access control

### Week 4: Chatbot Integration
- [ ] Design chatbot UI (sidebar in clinic dashboard)
- [ ] Implement patient history queries
- [ ] Implement allergy/medication queries
- [ ] Integrate with Gemini for natural language understanding
- [ ] Test with sample queries

---

## 8. SECURITY CONSIDERATIONS

1. **Password Security**: Use bcrypt for password hashing (min 10 rounds)
2. **OTP Security**: 
   - 6-digit OTP, 5-minute expiry
   - Rate limit: Max 3 OTP requests per 15 minutes
   - Max 3 OTP verification attempts before lockout
3. **JWT Tokens**: 
   - 24-hour expiry for clinic logins
   - 30-day expiry for patient logins
   - Refresh token mechanism
4. **Cross-Clinic Access**: 
   - Patient must explicitly authorize via OTP
   - Clinic cannot access patient data without authorization
   - Audit log all access attempts
5. **Data Privacy**: 
   - Encrypt sensitive fields (allergies, conditions) at rest
   - HTTPS only for all API calls
   - No sensitive data in logs

---

## 9. CHATBOT INTEGRATION (Sidebar)

### Chatbot UI (Clinic Dashboard Sidebar)

```html
<!-- CHATBOT SIDEBAR -->
<div class="chatbot-sidebar">
  <div class="chatbot-header">
    <h3>CliniqAI Assistant</h3>
    <p>Ask about patient history, allergies, medications</p>
  </div>
  
  <div class="chatbot-messages" id="chat-messages">
    <!-- Messages populated here -->
  </div>
  
  <div class="chatbot-input-group">
    <input 
      id="chat-input" 
      type="text" 
      placeholder="Ask about patient history..."
      onkeydown="if(event.key==='Enter') sendChatMessage()"
    />
    <button onclick="sendChatMessage()">Send</button>
  </div>
  
  <!-- Quick Buttons -->
  <div class="quick-buttons">
    <button onclick="askAboutAllergies()">Allergies</button>
    <button onclick="askAboutMedications()">Medications</button>
    <button onclick="askAboutHistory()">History</button>
  </div>
</div>
```

### Chatbot Query Examples

```
User: "What allergies does this patient have?"
Bot: "This patient has documented allergies to:
     • Penicillin (since 2025-10-12)
     • Aspirin (since 2025-09-05)
     
     ⚠️ Any new prescription with these or related drugs will trigger an alert."

User: "What medicines is the patient currently on?"
Bot: "Current active medications:
     • Amlodipine 5mg (1x/day) - for hypertension
     • Metformin 500mg (2x/day) - for diabetes
     
     Last updated: 2026-05-20"

User: "Show me all visits in the last 3 months"
Bot: "Visits in last 3 months:
     1. 2026-05-20 - Dr. Sharma's Clinic (Fever)
     2. 2026-05-10 - City Hospital (Hypertension check)
     3. 2026-04-15 - Apollo Hospital (Diabetes review)"
```

---

## 10. DEMO SCRIPT FOR JUDGES

```
SCENE 1: Clinic Login
- Doctor logs in with Clinic ID + Doctor ID + Password
- Dashboard loads with patient search

SCENE 2: Patient Search (New Clinic)
- Doctor enters patient's mobile number
- System shows "Patient not authorized at this clinic"
- Doctor sends authorization OTP
- (Simulate) Patient receives SMS and authorizes
- Patient's complete history appears (from other clinics)

SCENE 3: Cross-Clinic Alert (THE WOW MOMENT)
- Doctor uploads a new prescription
- Gemini extracts: Amoxicillin prescribed
- System checks patient's history
- RED ALERT appears: "Patient allergic to Penicillin since Oct 2025 at Apollo Hospital"
- Alert shows: "Amoxicillin is a penicillin-based antibiotic"
- Doctor acknowledges and cancels prescription

SCENE 4: Patient Portal
- Switch to patient view
- Show health timeline with visits from multiple clinics
- Show consolidated medications
- Show allergies prominently

JUDGES' TAKEAWAY:
"This is not just a clinic tool. This is a health information exchange that 
could prevent a patient death by catching a drug conflict across clinics."
```

---

This is the complete Phase 2 implementation guide. Ready to code?
