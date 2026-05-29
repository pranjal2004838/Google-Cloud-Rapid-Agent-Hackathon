# AI Chatbot Integration Guide
## Clinic Dashboard Zone 4: Intelligent Patient Record Assistant

---

## Overview

Add a **4th Zone** to the Clinic Dashboard: **AI Chatbot Assistant**

This chatbot will:
- Fetch patient records in real-time
- Answer natural language queries about patient history
- Check for allergies, past medications, conditions
- Provide quick verification without manual record searching
- Aid doctors in making informed decisions quickly

**Example Queries:**
```
"Does patient 9885904489 have any allergies related to paracetamol?"
"What medicines is this patient currently on?"
"Has this patient had any previous reactions to antibiotics?"
"Show me all visits in the last 3 months"
"Is there any drug interaction between Amlodipine and Simvastatin for this patient?"
```

---

## Architecture Changes

### Frontend Changes (Clinic Dashboard)

#### New Zone 4: AI Chatbot Sidebar

```html
<!-- ZONE 4: AI CHATBOT ASSISTANT -->
<aside class="w-80 bg-white border-l border-gray-200 flex flex-col p-4 shrink-0">
  <!-- CHATBOT HEADER -->
  <div class="mb-4 pb-4 border-b border-gray-200">
    <h3 class="font-semibold text-sm">CliniqAI Assistant</h3>
    <p class="text-xs text-gray-400 mt-1">Ask about patient history, allergies, medications</p>
  </div>

  <!-- CHAT MESSAGES AREA -->
  <div id="chat-messages" class="flex-1 overflow-y-auto mb-4 space-y-3">
    <!-- Messages will be populated here -->
    <div class="bg-blue-50 rounded-lg p-3 text-sm">
      <p class="text-blue-900">Hi! I'm your AI assistant. Ask me anything about the patient's history.</p>
      <p class="text-xs text-blue-700 mt-2">Example: "Does this patient have any allergies?"</p>
    </div>
  </div>

  <!-- QUICK BUTTONS -->
  <div class="grid grid-cols-2 gap-2 mb-4">
    <button onclick="askChatbot('allergies')" class="text-xs bg-emerald-50 text-emerald-700 border border-emerald-200 rounded px-2 py-1 hover:bg-emerald-100">
      Allergies
    </button>
    <button onclick="askChatbot('medications')" class="text-xs bg-emerald-50 text-emerald-700 border border-emerald-200 rounded px-2 py-1 hover:bg-emerald-100">
      Medications
    </button>
    <button onclick="askChatbot('history')" class="text-xs bg-emerald-50 text-emerald-700 border border-emerald-200 rounded px-2 py-1 hover:bg-emerald-100">
      Visit History
    </button>
    <button onclick="askChatbot('interactions')" class="text-xs bg-emerald-50 text-emerald-700 border border-emerald-200 rounded px-2 py-1 hover:bg-emerald-100">
      Interactions
    </button>
  </div>

  <!-- CHAT INPUT -->
  <div class="flex gap-2">
    <input 
      id="chat-input" 
      type="text" 
      placeholder="Ask about patient..." 
      class="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-400"
      onkeydown="if(event.key==='Enter') sendChatMessage()"
    />
    <button 
      onclick="sendChatMessage()" 
      class="bg-emerald-600 text-white rounded-lg px-3 py-2 text-sm hover:bg-emerald-700"
    >
      Send
    </button>
  </div>

  <!-- LOADING INDICATOR -->
  <div id="chat-loading" class="hidden text-xs text-gray-500 text-center mt-2">
    <span class="inline-block animate-spin">⟳</span> AI is thinking...
  </div>
</aside>
```

#### Updated Clinic Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ HEADER: Upload & extract document  │  Alert Badge  │  MongoDB Badge │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ ZONE 1: PATIENT  │ ZONE 2: UPLOAD │ ZONE 3: ALERTS │ ZONE 4: CHAT  │
│ SEARCH           │ & EXTRACTION   │ SYSTEM         │ ASSISTANT     │
│                  │                │                │               │
│ Search box       │ Drop zone      │ RED ALERT      │ Messages      │
│ Patient card     │ Extract button │ YELLOW ALERT   │ Quick buttons │
│ Recent patients  │ Progress       │ GREEN OK       │ Input field   │
│                  │                │                │               │
└─────────────────────────────────────────────────────────────────────┘
```

#### JavaScript Functions for Chatbot

```javascript
// Global variable to store current patient mobile number
let currentPatientMobile = null;

// Send chat message
async function sendChatMessage() {
  const input = document.getElementById('chat-input');
  const query = input.value.trim();
  
  if (!query) return;
  
  if (!currentPatientMobile) {
    addChatMessage('bot', 'Please search for a patient first.');
    return;
  }
  
  // Add user message to chat
  addChatMessage('user', query);
  input.value = '';
  
  // Show loading indicator
  document.getElementById('chat-loading').classList.remove('hidden');
  
  try {
    // Send query to backend
    const response = await fetch('/api/clinic/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({
        query: query,
        mobile_number: currentPatientMobile
      })
    });
    
    if (!response.ok) throw new Error('Chat request failed');
    
    const data = await response.json();
    
    // Add bot response to chat
    addChatMessage('bot', data.answer);
    
  } catch (error) {
    addChatMessage('bot', 'Sorry, I encountered an error. Please try again.');
    console.error('Chat error:', error);
  } finally {
    document.getElementById('chat-loading').classList.add('hidden');
  }
}

// Add message to chat
function addChatMessage(sender, message) {
  const messagesDiv = document.getElementById('chat-messages');
  const messageDiv = document.createElement('div');
  
  if (sender === 'user') {
    messageDiv.className = 'bg-emerald-50 rounded-lg p-3 text-sm text-right';
    messageDiv.innerHTML = `<p class="text-emerald-900">${escapeHtml(message)}</p>`;
  } else {
    messageDiv.className = 'bg-gray-50 rounded-lg p-3 text-sm text-left';
    messageDiv.innerHTML = `<p class="text-gray-900">${escapeHtml(message)}</p>`;
  }
  
  messagesDiv.appendChild(messageDiv);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Quick button handlers
function askChatbot(type) {
  const queries = {
    'allergies': `What allergies does patient ${currentPatientMobile} have?`,
    'medications': `What medicines is patient ${currentPatientMobile} currently on?`,
    'history': `Show me the visit history for patient ${currentPatientMobile} in the last 3 months`,
    'interactions': `Check for drug interactions for patient ${currentPatientMobile}`
  };
  
  document.getElementById('chat-input').value = queries[type];
  sendChatMessage();
}

// Update current patient when searching
function updateCurrentPatient(mobileNumber) {
  currentPatientMobile = mobileNumber;
  
  // Clear chat messages
  document.getElementById('chat-messages').innerHTML = `
    <div class="bg-blue-50 rounded-lg p-3 text-sm">
      <p class="text-blue-900">Patient ${mobileNumber} selected.</p>
      <p class="text-xs text-blue-700 mt-2">Ask me anything about this patient's history.</p>
    </div>
  `;
}

// Utility function to escape HTML
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
```

---

## Backend Changes (Phase 1 & Phase 2)

### New API Endpoint

```python
# POST /api/clinic/chat
# Input: {query, mobile_number, token}
# Output: {answer, confidence, sources}
```

### Backend Implementation

#### 1. Add to `agent/server.py`

```python
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthCredential
from google import genai
import os

app = FastAPI()
security = HTTPBearer()

@app.post("/api/clinic/chat")
async def chat_with_patient_context(
    query: str,
    mobile_number: str,
    credentials: HTTPAuthCredential = Depends(security)
):
    """
    AI Chatbot endpoint that answers questions about patient history.
    
    The chatbot:
    1. Verifies the doctor's token
    2. Checks clinic authorization
    3. Fetches patient records from MongoDB
    4. Uses Gemini to answer questions about the patient
    5. Returns the answer with confidence score
    """
    
    try:
        # Verify JWT token
        token = credentials.credentials
        payload = verify_jwt_token(token)
        clinic_id = payload.get("clinic_id")
        doctor_id = payload.get("doctor_id")
        
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Find patient
    patient = db.patients.find_one({"mobile_number": mobile_number})
    if not patient:
        return {
            "answer": f"Patient {mobile_number} not found in the system.",
            "confidence": 1.0,
            "sources": []
        }
    
    # Check if clinic is authorized to access this patient
    authorized = any(
        c["clinic_id"] == clinic_id and c["access_status"] == "active"
        for c in patient.get("authorized_clinics", [])
    )
    
    if not authorized:
        return {
            "answer": f"You are not authorized to access patient {mobile_number}'s records.",
            "confidence": 1.0,
            "sources": []
        }
    
    # Build patient context from MongoDB
    patient_context = build_patient_context(patient)
    
    # Use Gemini to answer the query
    answer = query_gemini_with_patient_context(query, patient_context)
    
    return {
        "answer": answer,
        "confidence": 0.95,  # You can calculate actual confidence from Gemini
        "sources": ["Patient Records", "Medical History"]
    }


def build_patient_context(patient: dict) -> str:
    """
    Build a comprehensive context string from patient data.
    This will be passed to Gemini for answering questions.
    """
    
    context = f"""
PATIENT INFORMATION:
Name: {patient.get('patient_name', 'Unknown')}
Mobile: {patient.get('mobile_number')}
Age: {patient.get('age', 'Unknown')}
Gender: {patient.get('gender', 'Unknown')}
Blood Group: {patient.get('blood_group', 'Unknown')}

KNOWN ALLERGIES:
{format_allergies(patient.get('known_allergies', []))}

CHRONIC CONDITIONS:
{format_conditions(patient.get('chronic_conditions', []))}

CURRENT ACTIVE MEDICATIONS:
{format_active_medications(patient.get('active_medications', []))}

RECENT VISIT HISTORY (Last 6 months):
{format_recent_visits(patient.get('visits', []))}

PAST MEDICATIONS (Last 12 months):
{format_past_medications(patient.get('visits', []))}
"""
    
    return context


def format_allergies(allergies: list) -> str:
    """Format allergies for context"""
    if not allergies:
        return "No known allergies recorded."
    
    return "\n".join([f"- {allergy}" for allergy in allergies])


def format_conditions(conditions: list) -> str:
    """Format chronic conditions for context"""
    if not conditions:
        return "No chronic conditions recorded."
    
    return "\n".join([f"- {condition}" for condition in conditions])


def format_active_medications(medications: list) -> str:
    """Format active medications for context"""
    if not medications:
        return "No active medications."
    
    result = []
    for med in medications:
        result.append(
            f"- {med.get('medicine_name')} {med.get('dosage')} "
            f"({med.get('frequency')}) - "
            f"Prescribed by {med.get('prescribed_by_clinic')} "
            f"on {med.get('prescribed_date')}"
        )
    
    return "\n".join(result)


def format_recent_visits(visits: list) -> str:
    """Format recent visits for context"""
    if not visits:
        return "No visit history."
    
    # Get last 6 months of visits
    from datetime import datetime, timedelta
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    
    recent_visits = [
        v for v in visits 
        if v.get('visit_date') and v['visit_date'] > six_months_ago
    ]
    
    if not recent_visits:
        return "No visits in the last 6 months."
    
    result = []
    for visit in sorted(recent_visits, key=lambda x: x.get('visit_date'), reverse=True):
        result.append(
            f"- {visit.get('visit_date').strftime('%Y-%m-%d')}: "
            f"{visit.get('diagnosis')} at {visit.get('clinic_name')} "
            f"(Dr. {visit.get('doctor_name')})"
        )
    
    return "\n".join(result)


def format_past_medications(visits: list) -> str:
    """Format past medications from visits"""
    if not visits:
        return "No medication history."
    
    all_medications = {}
    
    for visit in visits:
        for med in visit.get('medicines', []):
            med_name = med.get('name', 'Unknown').lower()
            if med_name not in all_medications:
                all_medications[med_name] = {
                    'name': med.get('name'),
                    'visits': []
                }
            all_medications[med_name]['visits'].append({
                'date': visit.get('visit_date'),
                'clinic': visit.get('clinic_name'),
                'dosage': med.get('dosage')
            })
    
    result = []
    for med_name, med_data in all_medications.items():
        result.append(
            f"- {med_data['name']}: Used in {len(med_data['visits'])} visit(s)"
        )
    
    return "\n".join(result)


def query_gemini_with_patient_context(query: str, patient_context: str) -> str:
    """
    Use Gemini to answer a question about the patient.
    """
    
    client = genai.Client(
        vertexai=True,
        project=os.environ['GOOGLE_CLOUD_PROJECT'],
        location=os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')
    )
    
    prompt = f"""You are a medical assistant helping a doctor understand patient records.

{patient_context}

DOCTOR'S QUESTION: {query}

INSTRUCTIONS:
1. Answer the question based ONLY on the patient information provided above.
2. If the answer is not in the records, say "This information is not available in the patient records."
3. Be concise and clear.
4. If the question is about allergies or drug interactions, be extra careful and explicit.
5. Always mention the source (e.g., "According to records from [clinic name]")
6. If there's a potential safety concern, highlight it clearly.

ANSWER:"""
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt]
    )
    
    return response.text
```

#### 2. Add Helper Functions to `agent/tools/alert_tool.py`

```python
def check_allergy_to_medicine(patient_allergies: list, medicine_name: str) -> dict:
    """
    Check if a patient has any allergies related to a specific medicine.
    
    Example:
    check_allergy_to_medicine(['penicillin'], 'paracetamol')
    → {"has_allergy": False, "message": "No allergies related to paracetamol"}
    
    check_allergy_to_medicine(['penicillin'], 'amoxicillin')
    → {"has_allergy": True, "message": "Patient allergic to penicillin. Amoxicillin is a penicillin-based antibiotic."}
    """
    
    medicine_lower = medicine_name.lower()
    
    for allergy in patient_allergies:
        allergy_lower = allergy.lower()
        
        # Check direct match
        for family, drugs in ALLERGY_FAMILIES.items():
            if allergy_lower in drugs or allergy_lower == family:
                for drug in drugs:
                    if drug in medicine_lower or medicine_lower in drug:
                        return {
                            "has_allergy": True,
                            "allergy": allergy,
                            "medicine": medicine_name,
                            "family": family,
                            "message": f"Patient allergic to {allergy}. {medicine_name} is in the same drug family ({family})."
                        }
    
    return {
        "has_allergy": False,
        "message": f"No allergies related to {medicine_name} in patient records."
    }


def get_drug_interactions_for_patient(
    patient_current_medicines: list,
    new_medicine: str
) -> dict:
    """
    Check if a new medicine has any interactions with patient's current medicines.
    
    Example:
    get_drug_interactions_for_patient(
        ['warfarin', 'aspirin'],
        'ibuprofen'
    )
    → {"has_interactions": True, "interactions": [...]}
    """
    
    interactions = []
    new_med_lower = new_medicine.lower()
    current_meds_lower = [m.lower() for m in patient_current_medicines]
    
    for (drug_a, drug_b), (severity, message) in DANGEROUS_COMBOS.items():
        if (drug_a in new_med_lower or new_med_lower in drug_a) and \
           any(drug_b in m or m in drug_b for m in current_meds_lower):
            interactions.append({
                "severity": severity,
                "drug_a": drug_a,
                "drug_b": drug_b,
                "message": message
            })
    
    return {
        "has_interactions": len(interactions) > 0,
        "interaction_count": len(interactions),
        "interactions": interactions
    }
```

#### 3. Update `agent/server.py` to Handle Chatbot Queries

```python
# Add these imports at the top
from agent.tools.alert_tool import check_allergy_to_medicine, get_drug_interactions_for_patient

# Enhance the query_gemini_with_patient_context function
def query_gemini_with_patient_context(query: str, patient_context: str, patient_data: dict = None) -> str:
    """
    Enhanced version that can handle specific medical queries.
    """
    
    query_lower = query.lower()
    
    # Check if query is about allergies
    if 'allerg' in query_lower:
        return handle_allergy_query(query, patient_data)
    
    # Check if query is about drug interactions
    if 'interact' in query_lower or 'combination' in query_lower:
        return handle_interaction_query(query, patient_data)
    
    # Check if query is about medications
    if 'medicin' in query_lower or 'drug' in query_lower:
        return handle_medication_query(query, patient_data)
    
    # Default: Use Gemini for general queries
    return query_gemini_general(query, patient_context)


def handle_allergy_query(query: str, patient_data: dict) -> str:
    """
    Handle allergy-related queries.
    Example: "Does patient have allergies related to paracetamol?"
    """
    
    patient_allergies = patient_data.get('known_allergies', [])
    
    if not patient_allergies:
        return f"Patient has no known allergies recorded in the system."
    
    # Try to extract medicine name from query
    medicine_name = extract_medicine_name(query)
    
    if medicine_name:
        result = check_allergy_to_medicine(patient_allergies, medicine_name)
        if result['has_allergy']:
            return f"⚠️ YES, patient has an allergy concern:\n\n{result['message']}\n\nAllergy: {result['allergy']}\nMedicine: {result['medicine']}"
        else:
            return f"✓ No, patient does not have allergies related to {medicine_name}.\n\nKnown allergies: {', '.join(patient_allergies)}"
    else:
        return f"Patient's known allergies:\n" + "\n".join([f"- {a}" for a in patient_allergies])


def handle_interaction_query(query: str, patient_data: dict) -> str:
    """
    Handle drug interaction queries.
    Example: "Is there any interaction between Amlodipine and Simvastatin?"
    """
    
    current_medicines = [m.get('medicine_name') for m in patient_data.get('active_medications', [])]
    
    if not current_medicines:
        return "Patient has no active medications recorded."
    
    # Try to extract medicine names from query
    medicine_names = extract_medicine_names(query)
    
    if medicine_names:
        interactions_found = []
        for med in medicine_names:
            result = get_drug_interactions_for_patient(current_medicines, med)
            if result['has_interactions']:
                interactions_found.extend(result['interactions'])
        
        if interactions_found:
            response = f"⚠️ Found {len(interactions_found)} potential interaction(s):\n\n"
            for interaction in interactions_found:
                response += f"- {interaction['message']} (Severity: {interaction['severity']})\n"
            return response
        else:
            return f"✓ No interactions found between {', '.join(medicine_names)} and patient's current medications."
    else:
        return f"Patient's current medications:\n" + "\n".join([f"- {m}" for m in current_medicines])


def handle_medication_query(query: str, patient_data: dict) -> str:
    """
    Handle medication-related queries.
    Example: "What medicines is the patient currently on?"
    """
    
    active_meds = patient_data.get('active_medications', [])
    
    if not active_meds:
        return "Patient has no active medications recorded."
    
    response = "Patient's current medications:\n\n"
    for med in active_meds:
        response += f"- {med.get('medicine_name')} {med.get('dosage')} ({med.get('frequency')})\n"
        response += f"  Prescribed by {med.get('prescribed_by_clinic')} on {med.get('prescribed_date')}\n\n"
    
    return response


def extract_medicine_name(query: str) -> str:
    """
    Extract medicine name from query.
    This is a simple implementation - can be enhanced with NLP.
    """
    
    # Common medicines list (can be expanded)
    common_medicines = [
        'paracetamol', 'ibuprofen', 'aspirin', 'amoxicillin', 'penicillin',
        'amlodipine', 'simvastatin', 'metformin', 'atorvastatin', 'lisinopril',
        'cough syrup', 'antibiotic', 'painkiller'
    ]
    
    query_lower = query.lower()
    
    for med in common_medicines:
        if med in query_lower:
            return med
    
    return None


def extract_medicine_names(query: str) -> list:
    """
    Extract multiple medicine names from query.
    """
    
    common_medicines = [
        'paracetamol', 'ibuprofen', 'aspirin', 'amoxicillin', 'penicillin',
        'amlodipine', 'simvastatin', 'metformin', 'atorvastatin', 'lisinopril',
        'cough syrup', 'antibiotic', 'painkiller'
    ]
    
    query_lower = query.lower()
    found_meds = []
    
    for med in common_medicines:
        if med in query_lower:
            found_meds.append(med)
    
    return found_meds


def query_gemini_general(query: str, patient_context: str) -> str:
    """
    Use Gemini for general queries about patient.
    """
    
    client = genai.Client(
        vertexai=True,
        project=os.environ['GOOGLE_CLOUD_PROJECT'],
        location=os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')
    )
    
    prompt = f"""You are a medical assistant helping a doctor understand patient records.

{patient_context}

DOCTOR'S QUESTION: {query}

INSTRUCTIONS:
1. Answer based ONLY on the patient information provided.
2. If information is not available, say so clearly.
3. Be concise and clear.
4. Mention sources when relevant.
5. Highlight any safety concerns.

ANSWER:"""
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt]
    )
    
    return response.text
```

---

## Database Schema Updates

No changes needed to the database schema. The chatbot uses existing patient records.

---

## Example Chatbot Interactions

### Example 1: Allergy Check

```
Doctor: "Does patient 9885904489 have any allergies related to paracetamol?"

Backend:
1. Fetches patient record
2. Checks known_allergies: ["penicillin", "aspirin"]
3. Checks if paracetamol is in any allergy family
4. Returns: "No allergies related to paracetamol"

Chatbot Response:
"✓ No, patient does not have allergies related to paracetamol.

Known allergies: Penicillin, Aspirin"
```

### Example 2: Current Medications

```
Doctor: "What medicines is this patient currently on?"

Backend:
1. Fetches patient record
2. Extracts active_medications array
3. Formats with dosage, frequency, prescribed by

Chatbot Response:
"Patient's current medications:

- Amlodipine 5mg (1x/day)
  Prescribed by Dr. Sharma's Clinic on 2026-05-20

- Metformin 500mg (2x/day)
  Prescribed by City Hospital on 2026-04-15"
```

### Example 3: Drug Interaction Check

```
Doctor: "Is there any interaction between Amlodipine and Simvastatin?"

Backend:
1. Fetches patient record
2. Gets current medications: [Amlodipine, Metformin]
3. Checks DANGEROUS_COMBOS for interactions
4. Finds: ("amlodipine", "simvastatin") → MEDIUM severity

Chatbot Response:
"⚠️ Found 1 potential interaction:

- Simvastatin dose should not exceed 20mg with Amlodipine (Severity: MEDIUM)

Recommendation: Verify dosage with prescribing physician."
```

### Example 4: Visit History

```
Doctor: "Show me all visits in the last 3 months"

Backend:
1. Fetches patient record
2. Filters visits from last 3 months
3. Formats with date, diagnosis, clinic, doctor

Chatbot Response:
"Recent visit history (Last 3 months):

- 2026-05-20: Viral Fever at Dr. Sharma's Clinic (Dr. Sharma)
- 2026-05-10: Hypertension Check at City Hospital (Dr. Patel)
- 2026-04-15: Diabetes Review at Apollo Hospital (Dr. Gupta)"
```

---

## Frontend Layout Changes

### Updated Clinic Dashboard (4 Zones)

```
CLINIC DASHBOARD
┌──────────────────────────────────────────────────────────────────┐
│ HEADER: Upload & extract | Alert Badge | MongoDB Connected       │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│ ZONE 1:        │ ZONE 2:      │ ZONE 3:      │ ZONE 4:          │
│ PATIENT        │ UPLOAD &     │ ALERT        │ AI CHATBOT       │
│ SEARCH         │ EXTRACTION   │ SYSTEM       │ ASSISTANT        │
│                │              │              │                  │
│ Search box     │ Drop zone    │ RED ALERT    │ Chat messages    │
│ Patient card   │ Extract btn  │ YELLOW ALERT │ Quick buttons    │
│ Recent list    │ Progress     │ GREEN OK     │ Input field      │
│                │              │              │                  │
│ Width: 20%     │ Width: 25%   │ Width: 25%   │ Width: 30%       │
│                │              │              │                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## API Endpoint Specification

### POST /api/clinic/chat

**Request:**
```json
{
  "query": "Does patient 9885904489 have any allergies related to paracetamol?",
  "mobile_number": "9885904489"
}

Headers:
{
  "Authorization": "Bearer <jwt_token>",
  "Content-Type": "application/json"
}
```

**Response:**
```json
{
  "answer": "✓ No, patient does not have allergies related to paracetamol.\n\nKnown allergies: Penicillin, Aspirin",
  "confidence": 0.95,
  "sources": ["Patient Records", "Medical History"],
  "query_type": "allergy_check"
}
```

---

## Implementation Checklist

### Phase 1 Changes (Backend)
- [ ] Add `/api/clinic/chat` endpoint in `agent/server.py`
- [ ] Implement `build_patient_context()` function
- [ ] Implement `query_gemini_with_patient_context()` function
- [ ] Add helper functions for formatting patient data
- [ ] Add `check_allergy_to_medicine()` to `alert_tool.py`
- [ ] Add `get_drug_interactions_for_patient()` to `alert_tool.py`
- [ ] Add medicine name extraction functions
- [ ] Test with sample queries

### Phase 2 Changes (Frontend)
- [ ] Add Zone 4 (Chatbot) to clinic dashboard HTML
- [ ] Add chatbot styling with Tailwind CSS
- [ ] Implement `sendChatMessage()` function
- [ ] Implement `addChatMessage()` function
- [ ] Implement `askChatbot()` quick button handlers
- [ ] Implement `updateCurrentPatient()` function
- [ ] Add chat message scrolling
- [ ] Add loading indicator
- [ ] Test with sample queries

---

## Security Considerations

1. **Token Verification:** All chat requests must include valid JWT token
2. **Authorization Check:** Verify clinic has access to patient records
3. **Rate Limiting:** Limit chat requests per doctor/clinic
4. **Audit Logging:** Log all chatbot queries for compliance
5. **Data Privacy:** Never log sensitive patient data
6. **Input Validation:** Sanitize all user inputs before processing

---

## Performance Optimization

1. **Caching:** Cache patient records for 5 minutes to reduce DB queries
2. **Lazy Loading:** Load chat messages incrementally
3. **Debouncing:** Debounce chat input to prevent rapid requests
4. **Parallel Processing:** Fetch patient data while Gemini processes query
5. **Response Streaming:** Stream Gemini responses for faster perceived performance

---

## Example Implementation Timeline

### Day 1: Backend Setup
- [ ] Create `/api/clinic/chat` endpoint
- [ ] Implement patient context building
- [ ] Test with Gemini API

### Day 2: Chatbot Logic
- [ ] Implement allergy checking
- [ ] Implement drug interaction checking
- [ ] Implement medication formatting

### Day 3: Frontend Integration
- [ ] Add chatbot UI to dashboard
- [ ] Implement chat message handling
- [ ] Add quick button handlers

### Day 4: Testing & Polish
- [ ] Test all query types
- [ ] Handle edge cases
- [ ] Optimize performance

---

## Future Enhancements

1. **NLP Enhancement:** Use advanced NLP for better medicine name extraction
2. **Vector Search:** Use MongoDB vector search for semantic queries
3. **Multi-turn Conversations:** Remember context across multiple messages
4. **Confidence Scoring:** Calculate actual confidence from Gemini responses
5. **Query Suggestions:** Suggest relevant queries based on patient data
6. **Export Functionality:** Export chat conversations for medical records
7. **Multi-language Support:** Support Hindi and other Indian languages
8. **Voice Input:** Add voice-to-text for hands-free queries

---

## Summary

The AI Chatbot Assistant adds a powerful 4th zone to the Clinic Dashboard that:

✅ **Reduces Doctor Workload:** No need to manually search through records
✅ **Improves Decision Making:** Quick access to relevant patient information
✅ **Enhances Safety:** Instant allergy and drug interaction checks
✅ **Saves Time:** Natural language queries instead of clicking through records
✅ **Provides Confidence:** Gemini-powered answers with source attribution

This makes the clinic dashboard more intelligent and user-friendly for busy doctors.
