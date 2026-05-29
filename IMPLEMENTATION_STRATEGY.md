# Implementation Strategy: Workable Ideas for Phase 2

This document outlines practical, hackathon-friendly approaches to implement the Dual-Platform HIE architecture.

---

## 1. AUTHENTICATION IMPLEMENTATION

### Option A: Simple JWT + Local Storage (Recommended for Hackathon)

**Pros:**
- No external auth service needed
- Fast to implement
- Works offline-first
- Good enough for demo

**Cons:**
- Less secure for production
- No refresh token mechanism
- No session revocation

**Implementation:**

```python
# backend/auth.py
import jwt
import bcrypt
from datetime import datetime, timedelta
from fastapi import HTTPException

SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

def verify_password(password: str, hash: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode(), hash.encode())

def create_jwt_token(data: dict, expires_in_hours: int = 24) -> str:
    """Create JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=expires_in_hours)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_jwt_token(token: str) -> dict:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Clinic Login Endpoint
@app.post("/api/auth/clinic-login")
async def clinic_login(clinic_id: str, doctor_id: str, password: str):
    """Clinic login with 3-factor authentication"""
    
    # Find clinic
    clinic = db.clinics.find_one({"clinic_id": clinic_id})
    if not clinic:
        raise HTTPException(status_code=401, detail="Clinic not found")
    
    # Find doctor in clinic
    doctor = next((d for d in clinic.get("doctors", []) if d["doctor_id"] == doctor_id), None)
    if not doctor:
        raise HTTPException(status_code=401, detail="Doctor not found")
    
    # Verify password
    if not verify_password(password, doctor["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid password")
    
    # Check if doctor is active
    if not doctor.get("is_active", False):
        raise HTTPException(status_code=403, detail="Doctor account is inactive")
    
    # Create JWT token
    token_data = {
        "user_type": "doctor",
        "clinic_id": clinic_id,
        "doctor_id": doctor_id,
        "doctor_name": doctor["doctor_name"]
    }
    token = create_jwt_token(token_data, expires_in_hours=24)
    
    # Update last_login
    db.clinics.update_one(
        {"clinic_id": clinic_id, "doctors.doctor_id": doctor_id},
        {"$set": {"doctors.$.last_login": datetime.utcnow()}}
    )
    
    return {
        "token": token,
        "doctor": {
            "doctor_id": doctor_id,
            "doctor_name": doctor["doctor_name"],
            "department": doctor.get("department", "")
        },
        "clinic": {
            "clinic_id": clinic_id,
            "clinic_name": clinic["clinic_name"]
        }
    }

# Patient OTP Login
import random
import string

@app.post("/api/auth/patient-send-otp")
async def patient_send_otp(mobile_number: str):
    """Send OTP to patient"""
    
    # Validate mobile number format
    if not mobile_number.startswith("+91-") or len(mobile_number) != 13:
        raise HTTPException(status_code=400, detail="Invalid mobile number format")
    
    # Generate 6-digit OTP
    otp = "".join(random.choices(string.digits, k=6))
    otp_expiry = datetime.utcnow() + timedelta(minutes=5)
    
    # Find or create patient
    patient = db.patients.find_one({"mobile_number": mobile_number})
    if not patient:
        # Create new patient
        db.patients.insert_one({
            "mobile_number": mobile_number,
            "patient_name": "Unknown",
            "age": None,
            "gender": None,
            "otp": otp,
            "otp_expiry": otp_expiry,
            "otp_verified": False,
            "known_allergies": [],
            "chronic_conditions": [],
            "authorized_clinics": [],
            "visits": [],
            "active_medications": [],
            "created_at": datetime.utcnow()
        })
    else:
        # Update existing patient
        db.patients.update_one(
            {"mobile_number": mobile_number},
            {"$set": {"otp": otp, "otp_expiry": otp_expiry}}
        )
    
    # Send SMS (using Twilio or AWS SNS)
    # For hackathon, you can print to console or use a mock service
    print(f"[SMS] {mobile_number}: Your CliniqAI code is {otp}")
    
    return {
        "message": "OTP sent to your phone",
        "otp_expiry_seconds": 300,
        "debug_otp": otp  # Remove in production!
    }

@app.post("/api/auth/patient-verify-otp")
async def patient_verify_otp(mobile_number: str, otp: str):
    """Verify OTP and login patient"""
    
    # Find patient
    patient = db.patients.find_one({"mobile_number": mobile_number})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Verify OTP
    if patient.get("otp") != otp:
        raise HTTPException(status_code=401, detail="Invalid OTP")
    
    # Check OTP expiry
    if datetime.utcnow() > patient.get("otp_expiry"):
        raise HTTPException(status_code=401, detail="OTP expired")
    
    # Mark as verified
    db.patients.update_one(
        {"mobile_number": mobile_number},
        {"$set": {"otp_verified": True, "otp": None}}
    )
    
    # Create JWT token (30-day expiry for patients)
    token_data = {
        "user_type": "patient",
        "mobile_number": mobile_number,
        "patient_name": patient.get("patient_name", "Unknown")
    }
    token = create_jwt_token(token_data, expires_in_hours=720)  # 30 days
    
    return {
        "token": token,
        "patient": {
            "mobile_number": mobile_number,
            "patient_name": patient.get("patient_name"),
            "age": patient.get("age"),
            "gender": patient.get("gender"),
            "known_allergies": patient.get("known_allergies", []),
            "chronic_conditions": patient.get("chronic_conditions", [])
        }
    }
```

**Frontend (JavaScript):**

```javascript
// Store token in localStorage
function loginClinic(clinicId, doctorId, password) {
    fetch('/api/auth/clinic-login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({clinic_id: clinicId, doctor_id: doctorId, password})
    })
    .then(r => r.json())
    .then(data => {
        localStorage.setItem('token', data.token);
        localStorage.setItem('user_type', 'doctor');
        localStorage.setItem('clinic_id', data.clinic.clinic_id);
        localStorage.setItem('doctor_id', data.doctor.doctor_id);
        window.location.href = '/clinic-dashboard.html';
    })
    .catch(err => alert('Login failed: ' + err));
}

// Get token from localStorage for API calls
function getAuthHeaders() {
    const token = localStorage.getItem('token');
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

// Logout
function logout() {
    localStorage.clear();
    window.location.href = '/login.html';
}
```

---

### Option B: Firebase Authentication (More Secure)

**Pros:**
- Production-grade security
- Built-in session management
- No need to manage passwords
- Easy to implement

**Cons:**
- Adds external dependency
- Requires Firebase setup
- Slightly slower for hackathon

**Implementation:**

```html
<!-- Include Firebase SDK -->
<script src="https://www.gstatic.com/firebasejs/10.0.0/firebase-app.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.0.0/firebase-auth.js"></script>

<script>
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "your-project.firebaseapp.com",
  projectId: "your-project",
  storageBucket: "your-project.appspot.com",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID"
};

firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();

// Clinic login
function loginClinic(email, password) {
    auth.signInWithEmailAndPassword(email, password)
        .then(userCredential => {
            // Get custom claims (clinic_id, doctor_id)
            userCredential.user.getIdTokenResult().then(idTokenResult => {
                console.log(idTokenResult.claims);
                window.location.href = '/clinic-dashboard.html';
            });
        })
        .catch(error => alert('Login failed: ' + error.message));
}

// Patient login with phone
function loginPatientWithPhone(phoneNumber) {
    const appVerifier = new firebase.auth.RecaptchaVerifier('recaptcha-container');
    auth.signInWithPhoneNumber(phoneNumber, appVerifier)
        .then(confirmationResult => {
            // Store for OTP verification
            window.confirmationResult = confirmationResult;
            showOTPInput();
        })
        .catch(error => alert('Error: ' + error.message));
}

function verifyOTP(otp) {
    window.confirmationResult.confirm(otp)
        .then(result => {
            window.location.href = '/patient-dashboard.html';
        })
        .catch(error => alert('Invalid OTP: ' + error.message));
}
</script>
```

**Recommendation:** Use **Option A** for hackathon (faster), migrate to **Option B** for production.

---

## 2. PATIENT SEARCH & AUTHORIZATION FLOW

### Implementation Approach

```python
# backend/patient_management.py

@app.get("/api/clinic/search-patient")
async def search_patient(mobile_number: str, token: str):
    """Search for patient and check authorization"""
    
    # Verify token
    try:
        payload = verify_jwt_token(token)
        clinic_id = payload.get("clinic_id")
        doctor_id = payload.get("doctor_id")
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Find patient
    patient = db.patients.find_one({"mobile_number": mobile_number})
    
    if not patient:
        return {"status": "not_found"}
    
    # Check if clinic is authorized
    authorized = any(
        c["clinic_id"] == clinic_id and c["access_status"] == "active"
        for c in patient.get("authorized_clinics", [])
    )
    
    if authorized:
        # Return full patient record
        return {
            "status": "found_authorized",
            "patient": {
                "mobile_number": patient["mobile_number"],
                "patient_name": patient.get("patient_name"),
                "age": patient.get("age"),
                "gender": patient.get("gender"),
                "blood_group": patient.get("blood_group"),
                "known_allergies": patient.get("known_allergies", []),
                "chronic_conditions": patient.get("chronic_conditions", []),
                "visits": patient.get("visits", []),
                "active_medications": patient.get("active_medications", [])
            }
        }
    else:
        # Return not authorized
        return {"status": "found_not_authorized"}

@app.post("/api/clinic/request-patient-access")
async def request_patient_access(mobile_number: str, clinic_id: str, doctor_id: str, token: str):
    """Request patient authorization via OTP"""
    
    # Verify token
    payload = verify_jwt_token(token)
    
    # Find patient
    patient = db.patients.find_one({"mobile_number": mobile_number})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Generate authorization OTP
    auth_otp = "".join(random.choices(string.digits, k=6))
    auth_otp_expiry = datetime.utcnow() + timedelta(minutes=5)
    
    # Store pending authorization
    db.pending_authorizations.insert_one({
        "mobile_number": mobile_number,
        "clinic_id": clinic_id,
        "otp": auth_otp,
        "otp_expiry": auth_otp_expiry,
        "created_at": datetime.utcnow()
    })
    
    # Get clinic name
    clinic = db.clinics.find_one({"clinic_id": clinic_id})
    clinic_name = clinic.get("clinic_name", "Unknown Clinic")
    
    # Send SMS
    print(f"[SMS] {mobile_number}: {clinic_name} requests access to your health records. Reply with OTP: {auth_otp}")
    
    return {"message": "Authorization OTP sent to patient"}

@app.post("/api/patient/authorize-clinic-access")
async def authorize_clinic_access(mobile_number: str, clinic_id: str, otp: str):
    """Patient authorizes clinic access"""
    
    # Find pending authorization
    auth_record = db.pending_authorizations.find_one({
        "mobile_number": mobile_number,
        "clinic_id": clinic_id,
        "otp": otp
    })
    
    if not auth_record:
        raise HTTPException(status_code=401, detail="Invalid OTP")
    
    if datetime.utcnow() > auth_record.get("otp_expiry"):
        raise HTTPException(status_code=401, detail="OTP expired")
    
    # Get clinic info
    clinic = db.clinics.find_one({"clinic_id": clinic_id})
    
    # Add clinic to authorized_clinics
    db.patients.update_one(
        {"mobile_number": mobile_number},
        {
            "$push": {
                "authorized_clinics": {
                    "clinic_id": clinic_id,
                    "clinic_name": clinic.get("clinic_name"),
                    "access_granted_date": datetime.utcnow(),
                    "access_status": "active",
                    "otp_verified": True
                }
            }
        }
    )
    
    # Delete pending authorization
    db.pending_authorizations.delete_one({"_id": auth_record["_id"]})
    
    return {"message": "Access granted"}
```

---

## 3. FRONTEND ARCHITECTURE

### Option A: Single HTML File with Client-Side Routing (Recommended)

**File Structure:**
```
cliniqai/
├── ui/
│   └── index.html          ← Single file with all screens
├── agent/
│   └── server.py           ← FastAPI backend
└── requirements.txt
```

**Pros:**
- Single deployment
- No build step
- Easy to manage
- Good for hackathon

**Cons:**
- Large HTML file
- All code in one place

**Implementation:**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>CliniqAI</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 font-sans text-gray-900">

<div id="app"></div>

<script>
// Simple client-side router
const routes = {
  '/': 'landing',
  '/clinic-login': 'clinic-login',
  '/patient-login': 'patient-login',
  '/clinic-dashboard': 'clinic-dashboard',
  '/patient-dashboard': 'patient-dashboard'
};

function navigate(path) {
  window.history.pushState({}, '', path);
  renderPage(path);
}

function renderPage(path) {
  const page = routes[path] || 'landing';
  const app = document.getElementById('app');
  
  switch(page) {
    case 'landing':
      app.innerHTML = renderLanding();
      break;
    case 'clinic-login':
      app.innerHTML = renderClinicLogin();
      break;
    case 'patient-login':
      app.innerHTML = renderPatientLogin();
      break;
    case 'clinic-dashboard':
      if (!isLoggedIn('doctor')) navigate('/clinic-login');
      else app.innerHTML = renderClinicDashboard();
      break;
    case 'patient-dashboard':
      if (!isLoggedIn('patient')) navigate('/patient-login');
      else app.innerHTML = renderPatientDashboard();
      break;
  }
}

function isLoggedIn(userType) {
  const token = localStorage.getItem('token');
  const type = localStorage.getItem('user_type');
  return token && type === userType;
}

function renderLanding() {
  return `
    <div class="flex items-center justify-center h-screen bg-gradient-to-br from-emerald-50 to-blue-50">
      <div class="text-center">
        <div class="text-6xl font-bold text-emerald-600 mb-4">CliniqAI</div>
        <p class="text-gray-600 mb-8">Centralized Health Information Exchange</p>
        
        <div class="space-y-4">
          <button onclick="navigate('/clinic-login')" class="block w-64 bg-emerald-600 text-white py-3 rounded-lg font-medium hover:bg-emerald-700">
            I'm a Healthcare Provider
          </button>
          <button onclick="navigate('/patient-login')" class="block w-64 bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700">
            I'm a Patient
          </button>
        </div>
      </div>
    </div>
  `;
}

function renderClinicLogin() {
  return `
    <div class="flex items-center justify-center h-screen bg-gray-50">
      <div class="w-96 bg-white rounded-lg shadow-lg p-8">
        <h2 class="text-2xl font-bold mb-6">Clinic Login</h2>
        
        <form onsubmit="handleClinicLogin(event)">
          <div class="mb-4">
            <label class="block text-sm font-medium mb-2">Clinic ID</label>
            <input type="text" id="clinic-id" class="w-full border border-gray-300 rounded-lg px-3 py-2" required />
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium mb-2">Doctor ID</label>
            <input type="text" id="doctor-id" class="w-full border border-gray-300 rounded-lg px-3 py-2" required />
          </div>
          
          <div class="mb-6">
            <label class="block text-sm font-medium mb-2">Password</label>
            <input type="password" id="password" class="w-full border border-gray-300 rounded-lg px-3 py-2" required />
          </div>
          
          <button type="submit" class="w-full bg-emerald-600 text-white py-2 rounded-lg font-medium hover:bg-emerald-700">
            LOGIN
          </button>
        </form>
        
        <button onclick="navigate('/')" class="w-full mt-4 text-gray-600 hover:text-gray-900">
          Back
        </button>
      </div>
    </div>
  `;
}

async function handleClinicLogin(event) {
  event.preventDefault();
  
  const clinicId = document.getElementById('clinic-id').value;
  const doctorId = document.getElementById('doctor-id').value;
  const password = document.getElementById('password').value;
  
  try {
    const response = await fetch('/api/auth/clinic-login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({clinic_id: clinicId, doctor_id: doctorId, password})
    });
    
    if (!response.ok) throw new Error('Login failed');
    
    const data = await response.json();
    localStorage.setItem('token', data.token);
    localStorage.setItem('user_type', 'doctor');
    localStorage.setItem('clinic_id', data.clinic.clinic_id);
    localStorage.setItem('doctor_id', data.doctor.doctor_id);
    
    navigate('/clinic-dashboard');
  } catch (err) {
    alert('Login failed: ' + err.message);
  }
}

// Initialize
window.addEventListener('popstate', () => renderPage(window.location.pathname));
renderPage(window.location.pathname);
</script>

</body>
</html>
```

---

### Option B: Separate HTML Files (More Modular)

**File Structure:**
```
cliniqai/
├── ui/
│   ├── index.html           ← Landing page
│   ├── clinic-login.html
│   ├── patient-login.html
│   ├── clinic-dashboard.html
│   └── patient-dashboard.html
├── agent/
│   └── server.py
└── requirements.txt
```

**Pros:**
- Cleaner file organization
- Easier to maintain
- Smaller individual files

**Cons:**
- Multiple files to manage
- Need to serve all files

**Recommendation:** Use **Option A** for hackathon (simpler), migrate to **Option B** for production.

---

## 4. CHATBOT IMPLEMENTATION

### Simple Approach: Pattern Matching + Gemini

```python
# backend/chatbot.py
from google import genai

@app.post("/api/clinic/chat")
async def chat_with_patient_context(query: str, mobile_number: str, token: str):
    """Chatbot that answers questions about patient"""
    
    # Verify token
    payload = verify_jwt_token(token)
    clinic_id = payload.get("clinic_id")
    
    # Check authorization
    patient = db.patients.find_one({"mobile_number": mobile_number})
    authorized = any(
        c["clinic_id"] == clinic_id and c["access_status"] == "active"
        for c in patient.get("authorized_clinics", [])
    )
    
    if not authorized:
        return {"error": "Not authorized to access this patient"}
    
    # Build context from patient data
    context = f"""
    Patient: {patient.get('patient_name')}
    Mobile: {mobile_number}
    Age: {patient.get('age')}
    Gender: {patient.get('gender')}
    
    Known Allergies: {', '.join(patient.get('known_allergies', []))}
    Chronic Conditions: {', '.join(patient.get('chronic_conditions', []))}
    
    Recent Visits:
    {format_visits(patient.get('visits', [])[-3:])}
    
    Current Medications:
    {format_medications(patient.get('active_medications', []))}
    """
    
    # Use Gemini to answer question
    client = genai.Client(vertexai=True, project=os.environ['GOOGLE_CLOUD_PROJECT'])
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            f"Patient Context:\n{context}\n\nQuestion: {query}\n\nAnswer briefly and accurately."
        ]
    )
    
    return {"answer": response.text}

def format_visits(visits):
    """Format visits for context"""
    return "\n".join([
        f"- {v.get('visit_date')}: {v.get('diagnosis')} at {v.get('clinic_name')}"
        for v in visits
    ])

def format_medications(meds):
    """Format medications for context"""
    return "\n".join([
        f"- {m.get('medicine_name')} {m.get('dosage')} ({m.get('frequency')})"
        for m in meds
    ])
```

---

## 5. SECURITY BEST PRACTICES

### Password Hashing

```python
import bcrypt

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=10)
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(password: str, hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), hash.encode())
```

### OTP Rate Limiting

```python
from datetime import datetime, timedelta

@app.post("/api/auth/patient-send-otp")
async def patient_send_otp(mobile_number: str):
    """Send OTP with rate limiting"""
    
    # Check rate limit
    recent_attempts = db.otp_attempts.count_documents({
        "mobile_number": mobile_number,
        "created_at": {"$gt": datetime.utcnow() - timedelta(minutes=15)}
    })
    
    if recent_attempts >= 3:
        raise HTTPException(status_code=429, detail="Too many OTP requests. Try again later.")
    
    # Generate and send OTP
    otp = "".join(random.choices(string.digits, k=6))
    
    db.otp_attempts.insert_one({
        "mobile_number": mobile_number,
        "otp": otp,
        "created_at": datetime.utcnow()
    })
    
    # Send SMS
    print(f"[SMS] {mobile_number}: {otp}")
    
    return {"message": "OTP sent"}
```

---

## 6. TESTING STRATEGY

### Unit Tests

```python
# tests/test_auth.py
import pytest
from fastapi.testclient import TestClient
from agent.server import app

client = TestClient(app)

def test_clinic_login_success():
    response = client.post("/api/auth/clinic-login", json={
        "clinic_id": "CLINIC_001",
        "doctor_id": "DOC_001",
        "password": "test_password"
    })
    assert response.status_code == 200
    assert "token" in response.json()

def test_clinic_login_invalid_password():
    response = client.post("/api/auth/clinic-login", json={
        "clinic_id": "CLINIC_001",
        "doctor_id": "DOC_001",
        "password": "wrong_password"
    })
    assert response.status_code == 401

def test_patient_otp_login():
    # Send OTP
    response = client.post("/api/auth/patient-send-otp", json={
        "mobile_number": "+91-9876543210"
    })
    assert response.status_code == 200
    
    # Verify OTP
    otp = response.json().get("debug_otp")
    response = client.post("/api/auth/patient-verify-otp", json={
        "mobile_number": "+91-9876543210",
        "otp": otp
    })
    assert response.status_code == 200
    assert "token" in response.json()
```

---

## 7. DEPLOYMENT CHECKLIST

- [ ] Change SECRET_KEY in production
- [ ] Remove debug_otp from responses
- [ ] Enable HTTPS only
- [ ] Set up proper logging
- [ ] Configure rate limiting
- [ ] Set up monitoring & alerts
- [ ] Test all auth flows
- [ ] Test cross-clinic authorization
- [ ] Verify OTP SMS delivery
- [ ] Load test the system

---

## Summary: Recommended Tech Stack for Hackathon

| Component | Technology | Reason |
|-----------|-----------|--------|
| Auth | JWT + bcrypt | Fast to implement, no external deps |
| OTP | Random 6-digit + SMS | Simple, ABHA-aligned |
| Frontend | Single HTML + Vanilla JS | No build step, easy to deploy |
| Backend | FastAPI + MongoDB | Fast, modern, easy to use |
| Chatbot | Gemini + pattern matching | Leverages existing Gemini integration |
| Deployment | Google Cloud Run | Free tier, easy deployment |

This approach gets you a working demo in 2-3 days, leaving time for polish and testing.

Ready to code?
