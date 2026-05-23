# CliniqAI — Complete Build Plan
### Google Cloud Rapid Agent Hackathon | MongoDB Track | Submission: June 11, 2026

---



---

## What Are We Building — In Plain English

**CliniqAI** is a Google-native clinical agent for small clinics, built on **Agent Development Kit (ADK) + Gemini on Vertex AI + Cloud Run**, with **MongoDB** as the memory and search layer.

Today, a doctor at a neighborhood clinic in Mumbai writes your name, medicines, and tests in a paper register or sends photos via WhatsApp. When you return six months later, they have no idea what you were prescribed. When you visit a different clinic, your history is invisible. Medicines get repeated. Allergies get ignored. Tests get re-done.

CliniqAI fixes this. The doctor or their assistant takes a photo of any paper document — a prescription, a lab report, a discharge summary — and the agent:
1. Uploads the document to **Cloud Storage** and reads it using **Gemini on Vertex AI** (even if handwritten, in Hindi or English)
2. Understands who the patient is, what medicines were given, what tests were done
3. Stores it as a clean, structured patient record in MongoDB
4. Lets the doctor search in plain English: *"Show me all patients on metformin"* or *"When did Ramesh Gupta last visit?"*
5. Flags important things automatically: *"This patient has a penicillin allergy — the new prescription includes amoxicillin"*

That last one is the jaw-dropper in the demo. That is what wins.

---

## The Tech Stack — Every Single Tool

| Tool | What It Is | Why We Use It | Cost |
|---|---|---|---|
| **Gemini 2.5 Flash on Vertex AI** | Google's multimodal model via Vertex AI | Multilingual handwriting extraction + structured medical parsing | Free tier / GCP credits |
| **Agent Development Kit (ADK)** | Google Cloud agent framework | Agentic reasoning + tool orchestration across vision, alerts, and DB tools | Free with GCP account |
| **Vertex AI** | Google Cloud AI platform | Managed Gemini runtime, model governance, production-ready inference path | Included in GCP usage |
| **Cloud Storage** | Google Cloud object storage | Stores uploaded source documents and gives traceable artifact links for demo/audit | Free tier |
| **MongoDB Atlas** | Cloud database | Stores all patient records, enables search | Free tier (512MB) |
| **MongoDB MCP Server** | Bridge between AI and database | Lets the agent INSERT, FIND, UPDATE records in MongoDB by just describing what to do | Free / open source |
| **Google Cloud Run** | Hosts the backend | Deploys the agent as a live URL — required by hackathon for hosted project link | Free tier |
| **Python** | Programming language | Used to write the agent logic | Free |
| **HTML + Tailwind CSS + Vanilla JS** | Web UI (single file) | Clean, professional interface — one `index.html` file that calls the FastAPI backend. Looks polished in the demo without needing React knowledge. | Free |
| **GitHub** | Code repository | Public repo — required by hackathon | Free |

**Total cost to build and submit: ₹0** (everything is free tier / GCP credits)

---

## The Architecture — How It All Connects

```
DOCTOR'S PHONE / COMPUTER
         |
    [Upload photo of prescription]
         |
         ▼
   HTML + TAILWIND UI (index.html)
   - Clean, professional interface
   - Upload button + query box + patient sidebar
         |
         ▼
   GOOGLE CLOUD RUN (FastAPI backend)
   - Receives upload + query requests
   - Hosts the ADK-powered service
         |
         ▼
   CLOUD STORAGE (source document store)
   - Stores original uploaded file
   - Returns object URI for traceability
         |
         ▼
   GOOGLE ADK AGENT (Orchestrator)
   - Agent Development Kit tool routing
   - Agentic reasoning over extraction + risk checks
   - Has tools it can call:
         |
    ┌────┬────────────────────┬────────────────────┐
    │    │                    │                    │
    ▼    ▼                    ▼                    ▼
[Gemini on Vertex AI]  [Alert Tool]        [MongoDB MCP Server]
- Multilingual OCR       - Real-time risk    - INSERT / FIND / UPDATE
- Structured parsing       alerting             patient records
- Confidence scoring     - Drug/allergy      - Search by medicine/condition
                           checks             - Aggregate + vector search
```

**The key point for judges:** This is a **Google-native agent system** (ADK + Gemini on Vertex AI + Cloud Run + Cloud Storage) with MongoDB MCP as persistent memory/search. MongoDB is not decoration; it is the recall layer that makes the agent usable in real clinics.

**Google hero moments to emphasize in README/demo:**
1. **Multilingual handwriting extraction** with Gemini on Vertex AI
2. **Agentic reasoning** through ADK (decide when to extract, store, search, alert)
3. **Tool orchestration** across Cloud Storage, Gemini, alert tool, and MongoDB MCP
4. **Real-time risk alerting** before the doctor proceeds

---

## Complete Step-by-Step Build Plan

### PHASE 0 — Setup (Day 1, ~3 hours)

**Step 1: Create accounts (if you don't have them)**
- Google Cloud account → cloud.google.com → click "Try Free" → get $300 credits
- MongoDB Atlas account → mongodb.com/atlas → create free M0 cluster (free forever)
- GitHub account → github.com

**Step 2: Create a new Google Cloud Project**
- Go to console.cloud.google.com
- Click "New Project" → name it `cliniqai-hackathon`
- Enable these APIs (search each in the console):
  - Vertex AI API
  - Cloud Run API
  - Cloud Build API
  - Cloud Storage API

**Step 3: Set up MongoDB Atlas**
- Create a free M0 cluster (select Mumbai region — ap-south-1)
- Create a database called `cliniqai`
- Create a collection called `patients`
- Get your connection string: looks like `mongodb+srv://username:password@cluster.mongodb.net/`
- Create a service account for MCP server access (Organization → Access Manager → Service Accounts)
- Create a Cloud Storage bucket for uploads, e.g. `cliniqai-documents-<project-id>`

**Step 4: Install tools on your computer**
```bash
# Install Python (if not already installed)
# Download from python.org — version 3.11 or above

# Install Google ADK
pip install google-adk

# Install MongoDB MCP Server
npm install -g mongodb-mcp-server
# (requires Node.js — download from nodejs.org)

# Install other Python packages
pip install google-genai google-cloud-storage pymongo python-dotenv pillow fastapi uvicorn
```

Add these to your `.env`:
```env
GOOGLE_CLOUD_PROJECT=your_project_id
GOOGLE_CLOUD_LOCATION=us-central1
GCS_UPLOAD_BUCKET=cliniqai-documents-your-project
MONGODB_URI=your_mongodb_connection_string
```

---

### PHASE 1 — Build the Core Agent (Days 2–5)

This is the heart of everything. The agent is a Python program that uses Google ADK.

**Step 5: Create your project folder structure**
```
cliniqai/
├── agent/
│   ├── __init__.py
│   ├── main_agent.py        ← The brain
│   ├── tools/
│   │   ├── vision_tool.py   ← Reads photos
│   │   └── alert_tool.py    ← Checks drug conflicts
├── ui/
│   └── index.html           ← HTML + Tailwind + JS frontend
├── .env                     ← Your secret keys (never commit this)
├── requirements.txt
└── README.md
```

**Step 6: Write the Vision Tool**

This tool reads a Cloud Storage-backed document image and extracts structured patient data using Gemini on Vertex AI.

```python
# agent/tools/vision_tool.py

from google import genai
import json
import base64
from PIL import Image
import io

def extract_from_prescription(image_bytes: bytes) -> dict:
    """
    Takes a photo of a prescription or lab report.
    Returns structured patient data as a Python dictionary.
    """
    
    client = genai.Client(vertexai=True, project=os.environ['GOOGLE_CLOUD_PROJECT'], location=os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1'))
    
    # Convert image to base64 for Gemini
    image = Image.open(io.BytesIO(image_bytes))
    
    prompt = """
    You are a medical data extraction assistant. 
    Look at this prescription or medical document carefully.
    
    Extract the following information and return ONLY a JSON object:
    {
        "patient_name": "full name or 'Unknown' if not visible",
        "patient_age": "age as number or null",
        "patient_gender": "Male/Female/Other or null",
        "visit_date": "date in YYYY-MM-DD format or today's date",
        "doctor_name": "doctor's name or null",
        "clinic_name": "clinic name or null",
        "diagnosis": ["list of conditions mentioned"],
        "medicines": [
            {
                "name": "medicine name",
                "dose": "dosage like 500mg",
                "frequency": "like twice daily",
                "duration": "like 5 days"
            }
        ],
        "tests_ordered": ["list of tests if any"],
        "allergies_mentioned": ["list of allergies if mentioned"],
        "notes": "any other important notes"
    }
    
    If the document is in Hindi, translate the content to English.
    Return ONLY the JSON, no explanation text.
    """
    
    response = client.models.generate_content(model='gemini-2.5-flash', contents=[prompt, image])
    
    # Parse the JSON response
    try:
        data = json.loads(response.text.strip())
    except:
        # If parsing fails, return what we got with an error flag
        data = {"error": "Could not parse", "raw": response.text}
    
    return data
```

**Step 7: Write the MongoDB MCP Integration**

This is what connects the agent to MongoDB. The MongoDB MCP server runs as a separate process, and the ADK agent communicates with it.

```python
# agent/main_agent.py

from google.adk import Agent, Tool
from google.adk.tools.mcp_tool import MCPTool
import os

# Connect to MongoDB MCP Server
# The MCP server runs locally and connects to your Atlas cluster
mongodb_mcp = MCPTool(
    server_command="npx",
    server_args=[
        "mongodb-mcp-server",
        "--connectionString", os.environ["MONGODB_URI"]
    ]
)

# Define our custom vision tool as an ADK Tool
from tools.vision_tool import extract_from_prescription

vision_tool = Tool(
    name="extract_prescription_data",
    description="Reads a photo of a medical document and extracts patient information",
    function=extract_from_prescription
)

# Define the drug conflict checker
from tools.alert_tool import check_drug_conflicts

alert_tool = Tool(
    name="check_drug_conflicts",
    description="Checks if new medicines conflict with patient's known allergies or current medications",
    function=check_drug_conflicts
)

# BUILD THE MAIN AGENT
cliniqai_agent = Agent(
    name="CliniqAI",
    model="gemini-2.5-flash",
    
    instruction="""
    You are CliniqAI, a medical records assistant for small clinics.
    
    You help doctors and clinic staff by:
    1. Reading photos of prescriptions and medical documents
    2. Storing patient information in MongoDB
    3. Searching patient history when asked
    4. Flagging dangerous drug interactions or allergy conflicts
    
    When a doctor uploads a photo:
    - Call extract_prescription_data to read it
    - Use MongoDB to check if this patient already exists (search by name)
    - If patient exists, UPDATE their record with the new visit
    - If patient is new, INSERT a new patient document
    - ALWAYS check for drug conflicts after storing
    - Report back what was saved and any alerts
    
    When a doctor asks a question like "show me all diabetic patients":
    - Use MongoDB to search and return the answer in simple language
    - Always be concise and clear — doctors are busy
    
    MongoDB database: cliniqai
    MongoDB collection: patients
    
    Patient document structure:
    {
        "patient_id": "unique ID",
        "name": "Patient Name",
        "age": 45,
        "gender": "Male",
        "phone": "optional",
        "known_allergies": ["penicillin"],
        "conditions": ["diabetes", "hypertension"],
        "visits": [
            {
                "date": "2026-05-01",
                "doctor": "Dr. Sharma",
                "medicines": [...],
                "tests": [...],
                "notes": "..."
            }
        ]
    }
    """,
    
    tools=[vision_tool, alert_tool, mongodb_mcp]
)
```

**Step 8: Write the Drug Conflict Checker**

This is the feature that makes judges say "wow." The checker covers three layers: direct allergy matches, cross-allergy warnings (e.g. penicillin allergy → flag cephalosporins), and drug-drug interactions. All drug families are chosen for relevance to Indian primary care — nimesulide, aceclofenac, cotrimoxazole, and azithromycin are prescribed constantly in Indian clinics and were missing from the original version.

> **README note (important for credibility):** Add one sentence in your README stating that this is a demonstration-grade drug database for the hackathon prototype, and that a production system would use a clinical reference like DrugBank or RxNorm. This builds trust with judges rather than losing it.

```python
# agent/tools/alert_tool.py

# Drug family definitions — covers antibiotics, NSAIDs, ACE inhibitors,
# statins, and other classes common in Indian primary care.
ALLERGY_FAMILIES = {
    # Antibiotics
    "penicillin": [
        "amoxicillin", "ampicillin", "augmentin", "amoxyclav",
        "cloxacillin", "flucloxacillin", "piperacillin", "co-amoxiclav"
    ],
    "cephalosporin": [
        "cefalexin", "cefuroxime", "cefixime", "ceftriaxone",
        "cefpodoxime", "cefdinir", "cefadroxil"
        # Note: ~10% cross-reactivity with penicillin allergy
    ],
    "sulfonamide": [
        "cotrimoxazole", "bactrim", "septran", "sulfamethoxazole",
        "trimethoprim-sulfamethoxazole"
    ],
    "fluoroquinolone": [
        "ciprofloxacin", "ofloxacin", "levofloxacin", "norfloxacin",
        "moxifloxacin", "gatifloxacin"
    ],
    "macrolide": [
        "azithromycin", "erythromycin", "clarithromycin", "roxithromycin"
    ],

    # NSAIDs — very commonly prescribed in India
    "nsaid": [
        "ibuprofen", "diclofenac", "naproxen", "nimesulide",
        "aceclofenac", "piroxicam", "mefenamic acid", "ketorolac",
        "indomethacin", "combiflam"
    ],
    "aspirin": [
        "aspirin", "ecosprin", "disprin", "salicylate"
    ],

    # ACE inhibitors — cough is a known class effect
    "ace_inhibitor": [
        "ramipril", "enalapril", "lisinopril", "perindopril",
        "captopril", "trandolapril"
    ],

    # Statins
    "statin": [
        "atorvastatin", "rosuvastatin", "simvastatin",
        "lovastatin", "pitavastatin"
    ],
}

# Cross-allergy rules (clinically real — penicillin allergy has ~10%
# cross-reactivity with cephalosporins)
CROSS_ALLERGY_WARNINGS = {
    "penicillin": {
        "families": ["cephalosporin"],
        "message": "Possible cross-reactivity (~10%). Use with caution."
    },
    "nsaid": {
        "families": ["aspirin"],
        "message": "Aspirin belongs to the same anti-inflammatory group."
    }
}

# Drug-drug interactions — expanded for Indian primary care context.
# Format: (drug_a, drug_b): (severity, message)
DANGEROUS_COMBOS = {
    ("warfarin", "aspirin"):           ("HIGH",   "Serious bleeding risk — combined anticoagulation"),
    ("warfarin", "nsaid"):             ("HIGH",   "NSAIDs increase bleeding risk with warfarin"),
    ("warfarin", "ciprofloxacin"):     ("HIGH",   "Fluoroquinolones potentiate warfarin — monitor INR"),
    ("warfarin", "metronidazole"):     ("HIGH",   "Metronidazole strongly potentiates warfarin"),
    ("metformin", "contrast"):         ("HIGH",   "Hold metformin before contrast procedures — lactic acidosis risk"),
    ("ssri", "tramadol"):              ("HIGH",   "Serotonin syndrome risk"),
    ("ssri", "linezolid"):             ("HIGH",   "Severe serotonin syndrome risk"),
    ("digoxin", "amiodarone"):         ("HIGH",   "Amiodarone raises digoxin levels — toxicity risk"),
    ("lithium", "nsaid"):              ("HIGH",   "NSAIDs raise lithium levels — toxicity risk"),
    ("lithium", "ace_inhibitor"):      ("HIGH",   "ACE inhibitors raise lithium levels"),
    ("methotrexate", "nsaid"):         ("HIGH",   "NSAIDs reduce methotrexate clearance — toxicity"),
    ("methotrexate", "cotrimoxazole"): ("HIGH",   "Combined folate antagonism — severe toxicity"),
    ("amlodipine", "simvastatin"):     ("MEDIUM", "Simvastatin dose should not exceed 20mg with amlodipine"),
    ("metformin", "alcohol"):          ("MEDIUM", "Lactic acidosis risk increases with heavy alcohol use"),
    ("ace_inhibitor", "potassium"):    ("MEDIUM", "Hyperkalaemia risk — monitor potassium levels"),
    ("digoxin", "clarithromycin"):     ("MEDIUM", "Macrolides raise digoxin levels"),
    ("clopidogrel", "omeprazole"):     ("MEDIUM", "Omeprazole reduces clopidogrel effectiveness"),
    ("phenytoin", "fluconazole"):      ("MEDIUM", "Fluconazole raises phenytoin levels"),
    ("theophylline", "ciprofloxacin"): ("MEDIUM", "Ciprofloxacin raises theophylline — toxicity risk"),
}


def check_drug_conflicts(
    patient_allergies: list,
    current_medicines: list,
    new_medicines: list
) -> dict:
    """
    Checks three layers of conflict:
    1. Direct allergy — new medicine belongs to an allergenic drug family
    2. Cross-allergy — related family with known cross-reactivity
    3. Drug-drug interaction — new medicine combined with current medicines
    """
    alerts = []

    new_med_names = [m["name"].lower() for m in new_medicines]
    current_med_names = [m["name"].lower() for m in current_medicines]

    # Layer 1: Direct allergy check
    for allergy in patient_allergies:
        allergy_lower = allergy.lower()
        for family, drugs in ALLERGY_FAMILIES.items():
            if allergy_lower in drugs or allergy_lower == family:
                for new_name in new_med_names:
                    if any(d in new_name for d in drugs):
                        alerts.append({
                            "severity": "HIGH",
                            "type": "ALLERGY",
                            "message": (
                                f"ALLERGY ALERT: Patient allergic to {allergy}. "
                                f"New prescription includes '{new_name}' "
                                f"from the same drug family ({family})."
                            )
                        })

    # Layer 2: Cross-allergy check
    for allergy in patient_allergies:
        allergy_lower = allergy.lower()
        if allergy_lower in CROSS_ALLERGY_WARNINGS:
            rule = CROSS_ALLERGY_WARNINGS[allergy_lower]
            for related_family in rule["families"]:
                related_drugs = ALLERGY_FAMILIES.get(related_family, [])
                for new_name in new_med_names:
                    if any(d in new_name for d in related_drugs):
                        alerts.append({
                            "severity": "MEDIUM",
                            "type": "CROSS_ALLERGY",
                            "message": (
                                f"CROSS-ALLERGY WARNING: Patient allergic to {allergy}. "
                                f"'{new_name}' is a related drug. {rule['message']}"
                            )
                        })

    # Layer 3: Drug-drug interaction check (new vs current medicines)
    all_meds = current_med_names + new_med_names
    for (drug_a, drug_b), (severity, message) in DANGEROUS_COMBOS.items():
        a_present = any(drug_a in m for m in all_meds)
        b_present = any(drug_b in m for m in all_meds)
        if a_present and b_present:
            alerts.append({
                "severity": severity,
                "type": "INTERACTION",
                "message": f"DRUG INTERACTION ({severity}): {message}"
            })

    # Sort HIGH alerts to the top
    alerts.sort(key=lambda x: 0 if x["severity"] == "HIGH" else 1)

    return {
        "has_alerts": len(alerts) > 0,
        "alert_count": len(alerts),
        "high_severity": sum(1 for a in alerts if a["severity"] == "HIGH"),
        "alerts": alerts
    }
```

---

### PHASE 2 — Build the Web UI (Days 6–7)

The UI is what judges see in the demo video. Do not use Streamlit — it looks like every other hackathon project. Instead, write a single `ui/index.html` file using Tailwind CSS (CDN) and vanilla JS. It takes the same amount of time, calls the same FastAPI backend, and looks like a real product. The layout has three zones: a left sidebar for navigation and recent patients, a centre panel for document upload, and a right panel for the extracted record and alerts.

**Design principles to follow:**
- White background, thin borders, no gradients, no shadows
- Red alert box must be unmissable — large font, red background, red border
- "MongoDB connected" badge in the header makes the integration visible to judges
- Allergy conflict medicines should appear highlighted red in the medicines list

**Step 9: Write the HTML frontend**

```html
<!-- ui/index.html -->
<!-- Single file: Tailwind via CDN + vanilla JS. No build step needed. -->

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>CliniqAI</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 font-sans text-gray-900">

<div class="flex h-screen overflow-hidden">

  <!-- SIDEBAR -->
  <aside class="w-64 bg-white border-r border-gray-200 flex flex-col p-4 gap-4 shrink-0">
    <div class="flex items-center gap-2">
      <div class="w-8 h-8 bg-emerald-600 rounded-lg flex items-center justify-center text-white text-sm font-bold">C</div>
      <div>
        <div class="font-medium text-sm">CliniqAI</div>
        <div class="text-xs text-gray-400">Dr. Sharma's Clinic</div>
      </div>
    </div>

    <input id="search" type="text" placeholder="Search patients..."
      class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-400"
      onkeydown="if(event.key==='Enter') searchPatients()" />

    <nav class="flex flex-col gap-1 text-sm">
      <a class="px-3 py-2 rounded-lg bg-gray-100 font-medium">Upload document</a>
      <a class="px-3 py-2 rounded-lg text-gray-500 hover:bg-gray-50 cursor-pointer">All patients</a>
      <a class="px-3 py-2 rounded-lg text-gray-500 hover:bg-gray-50 cursor-pointer">Visit history</a>
      <a class="px-3 py-2 rounded-lg text-gray-500 hover:bg-gray-50 cursor-pointer">Drug alerts</a>
    </nav>

    <div class="mt-auto">
      <div class="text-xs text-gray-400 mb-2 uppercase tracking-wide">Today</div>
      <div class="grid grid-cols-2 gap-2">
        <div class="bg-gray-50 rounded-lg p-3">
          <div class="text-xs text-gray-400">Patients</div>
          <div class="text-xl font-medium" id="count-patients">24</div>
        </div>
        <div class="bg-gray-50 rounded-lg p-3">
          <div class="text-xs text-gray-400">Alerts</div>
          <div class="text-xl font-medium text-red-600" id="count-alerts">0</div>
        </div>
      </div>
    </div>
  </aside>

  <!-- MAIN AREA -->
  <main class="flex flex-col flex-1 overflow-hidden">

    <!-- TOP BAR -->
    <header class="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shrink-0">
      <div>
        <div class="font-medium text-sm">Upload & extract document</div>
        <div class="text-xs text-gray-400">Prescriptions · Lab reports · Discharge summaries · Hindi or English</div>
      </div>
      <div class="flex items-center gap-2">
        <span id="alert-badge" class="hidden text-xs bg-red-50 text-red-700 border border-red-200 px-2 py-1 rounded-full font-medium"></span>
        <span class="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded-full font-medium">MongoDB connected</span>
      </div>
    </header>

    <!-- TWO-COLUMN CONTENT -->
    <div class="flex flex-1 overflow-hidden">

      <!-- UPLOAD PANEL -->
      <section class="w-1/2 border-r border-gray-200 p-6 overflow-y-auto flex flex-col gap-4">
        <div class="text-sm font-medium text-gray-600">Document upload</div>

        <label id="drop-zone"
          class="border-2 border-dashed border-gray-200 rounded-xl p-8 text-center cursor-pointer hover:border-emerald-300 transition-colors">
          <div class="text-gray-400 text-3xl mb-2">&#8679;</div>
          <div class="text-sm text-gray-500">Drop prescription photo here</div>
          <div class="text-xs text-gray-400 mt-1">JPG · PNG · PDF · Works with handwriting</div>
          <input id="file-input" type="file" accept=".jpg,.jpeg,.png,.pdf" class="hidden" onchange="previewFile(event)" />
        </label>

        <img id="preview" class="hidden rounded-lg border border-gray-200 max-h-48 object-contain" />

        <button onclick="processDocument()"
          class="bg-emerald-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-emerald-700 transition-colors flex items-center justify-center gap-2">
          <span>&#9881;</span> Extract &amp; save to records
        </button>

        <div class="text-sm font-medium text-gray-600 mt-2">Ask anything</div>
        <div class="flex gap-2">
          <input id="query-input" type="text" placeholder="Show all patients on metformin..."
            class="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-400"
            onkeydown="if(event.key==='Enter') runQuery()" />
          <button onclick="runQuery()"
            class="bg-emerald-600 text-white rounded-lg px-3 py-2 text-sm hover:bg-emerald-700">&#8594;</button>
        </div>
        <div id="query-result" class="text-sm text-gray-600 bg-gray-50 rounded-lg p-3 hidden"></div>

        <!-- RECENT PATIENTS -->
        <div class="text-sm font-medium text-gray-600 mt-2">Recent patients</div>
        <div id="recent-list" class="flex flex-col gap-2"></div>
      </section>

      <!-- EXTRACTED RECORD PANEL -->
      <section class="w-1/2 p-6 overflow-y-auto flex flex-col gap-4">
        <div class="text-sm font-medium text-gray-600">Extracted record</div>

        <!-- Alert box — shown only when there are alerts -->
        <div id="alert-box" class="hidden border border-red-300 bg-red-50 rounded-xl p-4">
          <div class="text-red-700 font-medium text-sm mb-2">&#9888; Allergy conflict detected</div>
          <div id="alert-messages" class="text-red-600 text-sm leading-relaxed"></div>
        </div>

        <!-- OK box — shown when no alerts -->
        <div id="ok-box" class="hidden border border-green-200 bg-green-50 rounded-xl p-3 flex items-center gap-2 text-sm text-green-700">
          &#10003; No drug conflicts detected
        </div>

        <!-- Patient card -->
        <div id="patient-card" class="hidden border border-gray-200 rounded-xl p-4 bg-white">
          <div class="flex items-center gap-3 mb-4">
            <div id="patient-avatar"
              class="w-10 h-10 rounded-full bg-emerald-100 text-emerald-800 flex items-center justify-center font-medium text-sm shrink-0"></div>
            <div>
              <div id="patient-name" class="font-medium text-sm"></div>
              <div id="patient-meta" class="text-xs text-gray-400"></div>
            </div>
            <span id="returning-badge" class="hidden ml-auto text-xs bg-red-50 text-red-700 border border-red-200 px-2 py-1 rounded-full">Returning patient</span>
          </div>
          <table class="w-full text-sm">
            <tr class="border-b border-gray-100">
              <td class="py-1.5 text-gray-400 text-xs">Doctor</td>
              <td id="field-doctor" class="py-1.5 text-right text-xs"></td>
            </tr>
            <tr class="border-b border-gray-100">
              <td class="py-1.5 text-gray-400 text-xs">Visit date</td>
              <td id="field-date" class="py-1.5 text-right text-xs"></td>
            </tr>
            <tr class="border-b border-gray-100">
              <td class="py-1.5 text-gray-400 text-xs">Diagnosis</td>
              <td id="field-diagnosis" class="py-1.5 text-right text-xs"></td>
            </tr>
            <tr class="border-b border-gray-100">
              <td class="py-1.5 text-gray-400 text-xs">Known allergies</td>
              <td id="field-allergies" class="py-1.5 text-right text-xs font-medium"></td>
            </tr>
            <tr>
              <td class="py-1.5 text-gray-400 text-xs align-top">Medicines</td>
              <td id="field-medicines" class="py-1.5 text-right text-xs"></td>
            </tr>
          </table>
        </div>

        <!-- Saved confirmation -->
        <div id="saved-row" class="hidden bg-gray-50 border border-gray-200 rounded-lg p-3 flex items-center gap-2 text-xs text-gray-500">
          <span class="text-emerald-600 font-bold">&#10003;</span>
          <span id="saved-text"></span>
        </div>
      </section>

    </div>
  </main>
</div>

<script>
const API = 'http://localhost:8000';

document.getElementById('drop-zone').onclick = () =>
  document.getElementById('file-input').click();

function previewFile(event) {
  const file = event.target.files[0];
  if (!file) return;
  const preview = document.getElementById('preview');
  preview.src = URL.createObjectURL(file);
  preview.classList.remove('hidden');
}

async function processDocument() {
  const fileInput = document.getElementById('file-input');
  if (!fileInput.files[0]) { alert('Please select a file first.'); return; }
  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  const res = await fetch(`${API}/process`, { method: 'POST', body: formData });
  const result = await res.json();
  renderResult(result);
  loadRecent();
}

function renderResult(result) {
  const p = result.patient || {};
  const alerts = result.alerts || [];
  const hasHighAlert = alerts.some(a => a.severity === 'HIGH');

  // Show/hide alert boxes
  document.getElementById('alert-box').classList.toggle('hidden', alerts.length === 0);
  document.getElementById('ok-box').classList.toggle('hidden', alerts.length > 0);
  if (alerts.length > 0) {
    document.getElementById('alert-messages').innerHTML =
      alerts.map(a => `<div class="mb-1">${a.message}</div>`).join('');
    const badge = document.getElementById('alert-badge');
    badge.textContent = `${alerts.length} alert${alerts.length > 1 ? 's' : ''} today`;
    badge.classList.remove('hidden');
    document.getElementById('count-alerts').textContent = alerts.length;
  }

  // Patient card
  document.getElementById('patient-card').classList.remove('hidden');
  const initials = (p.name || 'UN').split(' ').map(n => n[0]).join('').slice(0,2).toUpperCase();
  document.getElementById('patient-avatar').textContent = initials;
  document.getElementById('patient-name').textContent = p.name || 'Unknown';
  document.getElementById('patient-meta').textContent =
    `${p.age || '—'} ${p.gender || ''} · ${p.visit_count > 1 ? p.visit_count + ' visits' : 'New patient'}`;
  document.getElementById('returning-badge').classList.toggle('hidden', !result.is_returning);
  document.getElementById('field-doctor').textContent = p.doctor || '—';
  document.getElementById('field-date').textContent = p.visit_date || '—';
  document.getElementById('field-diagnosis').textContent = (p.diagnosis || []).join(', ') || '—';

  const allergiesEl = document.getElementById('field-allergies');
  allergiesEl.textContent = (p.known_allergies || []).join(', ') || 'None';
  allergiesEl.className = `py-1.5 text-right text-xs font-medium ${hasHighAlert ? 'text-red-600' : 'text-gray-800'}`;

  const medsEl = document.getElementById('field-medicines');
  medsEl.innerHTML = (p.medicines || []).map(m => {
    const isConflict = alerts.some(a => a.message.toLowerCase().includes(m.name.toLowerCase()));
    const cls = isConflict ? 'text-red-600 font-medium' : 'text-blue-600';
    return `<span class="inline-block ${cls} mr-1 mb-1 text-xs px-2 py-0.5 bg-blue-50 rounded-full ${isConflict ? 'bg-red-50' : ''}">${m.name}</span>`;
  }).join('');

  // Saved row
  const savedRow = document.getElementById('saved-row');
  savedRow.classList.remove('hidden');
  document.getElementById('saved-text').textContent =
    `Record saved to MongoDB · patient_id: ${result.record_id || '—'} · Visit #${p.visit_count || 1} added`;
}

async function runQuery() {
  const q = document.getElementById('query-input').value.trim();
  if (!q) return;
  const res = await fetch(`${API}/query`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: q })
  });
  const data = await res.json();
  const box = document.getElementById('query-result');
  box.textContent = data.answer;
  box.classList.remove('hidden');
}

async function loadRecent() {
  const res = await fetch(`${API}/recent`);
  const data = await res.json();
  const list = document.getElementById('recent-list');
  list.innerHTML = (data.patients || []).map(p => `
    <div class="flex items-center gap-3 p-3 bg-gray-50 border border-gray-200 rounded-lg">
      <div class="w-8 h-8 rounded-full bg-emerald-100 text-emerald-800 flex items-center justify-center text-xs font-medium shrink-0">
        ${(p.name || 'UN').split(' ').map(n => n[0]).join('').slice(0,2).toUpperCase()}
      </div>
      <div class="flex-1 min-w-0">
        <div class="text-sm font-medium truncate">${p.name}</div>
        <div class="text-xs text-gray-400">${(p.conditions || []).join(' · ') || '—'}</div>
      </div>
      <span class="text-xs ${p.has_alerts ? 'bg-red-50 text-red-700 border-red-200' : 'bg-green-50 text-green-700 border-green-200'} border px-2 py-0.5 rounded-full shrink-0">
        ${p.has_alerts ? '⚠ Alert' : 'No alerts'}
      </span>
    </div>
  `).join('');
}

loadRecent();
</script>
</body>
</html>
```

---

### PHASE 3 — Deploy to Google Cloud (Days 8–9)

**Step 10: Create Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install Node.js for MongoDB MCP server
RUN apt-get update && apt-get install -y nodejs npm

# Install MongoDB MCP server
RUN npm install -g mongodb-mcp-server

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy code
COPY . .

# Expose port
EXPOSE 8080

# Start command
CMD ["python", "-m", "uvicorn", "agent.server:app", 
     "--host", "0.0.0.0", "--port", "8080"]
```

**Step 11: Deploy to Cloud Run**

```bash
# In your terminal, from the project folder:

# 1. Login to Google Cloud
gcloud auth login

# 2. Set your project
gcloud config set project cliniqai-hackathon

# 3. Build and deploy in one command
gcloud run deploy cliniqai \
  --source . \
  --region asia-south1 \
  --allow-unauthenticated \
  --set-env-vars MONGODB_URI="your-connection-string" \
  --set-env-vars GOOGLE_CLOUD_PROJECT="your-project-id",GOOGLE_CLOUD_LOCATION="us-central1",GCS_UPLOAD_BUCKET="your-bucket-name"

# You'll get a URL like: https://cliniqai-xxxxx-el.a.run.app
# THIS is your "hosted project URL" for the submission form
```

---

### PHASE 4 — Testing Your Agent (Day 9)

Before recording your demo, test these 5 scenarios:

**Test 1 — New patient from photo**
- Upload a photo of a handwritten prescription (write one yourself for testing)
- Agent should: extract info → check if patient exists → create new record → confirm saved

**Test 2 — Returning patient**
- Upload another prescription for the same patient name
- Agent should: find existing patient → add new visit to their record → show visit history

**Test 3 — Allergy alert**
- Create a patient record with "penicillin" in allergies
- Upload a prescription that includes "Amoxicillin"
- Agent should: extract → save → fire a HIGH severity alert

**Test 4 — Natural language search**
- Type: "Show all patients prescribed metformin"
- Agent should use MongoDB MCP to query and return matching patients

**Test 5 — Summary query**
- Type: "How many patients visited in May 2026?"
- Agent should use MongoDB aggregation and return a count

---

### PHASE 5 — The 3-Minute Demo Video (Day 10)

This is the most important thing you will do. Judges spend 3 minutes on your project. Make every second count.

**Exact script:**

| Time | What You Show | What You Say |
|---|---|---|
| 0:00–0:20 | Map of India, photo of a paper register | "700,000 small clinics in India still keep patient records on paper. When a patient returns, doctors have no history. When they change clinics, everything starts over." |
| 0:20–0:35 | Show the CliniqAI UI | "We built CliniqAI — an AI agent that digitizes any paper medical document in seconds and builds a searchable patient database." |
| 0:35–1:10 | Upload a photo of a handwritten prescription live | Watch the agent extract all data, show the structured record appearing in real time |
| 1:10–1:40 | Upload a second prescription for same patient — show it adds to history | "The agent recognizes returning patients and builds their complete medical timeline." |
| 1:40–2:10 | Upload a prescription with amoxicillin for a patient with penicillin allergy | Show the RED alert appear. Say: "The agent caught a dangerous allergy conflict — a penicillin-allergic patient being prescribed amoxicillin. This could have killed someone." |
| 2:10–2:35 | Type a query in the search box | "Doctors can ask anything in plain English — the agent queries MongoDB and answers instantly." |
| 2:35–3:00 | Show the architecture diagram briefly | "Built on Google Cloud Agent Builder, Gemini 3, and MongoDB Atlas with MCP for real-time database operations." |

**The allergy demo moment is your winning moment. Plan it, rehearse it, make the red alert visible and shocking.**

---

### PHASE 6 — GitHub Repository Setup

**What must be in your repo:**

```
README.md                    ← Detailed description (see template below)
LICENSE                      ← MIT License (copy from GitHub's template)
requirements.txt
Dockerfile
agent/
  main_agent.py
  tools/
    vision_tool.py
    alert_tool.py
ui/
  index.html
docs/
  architecture.png           ← Screenshot of your architecture diagram
  demo_screenshot_1.png
  demo_screenshot_2.png
```

**README.md must include:**
- What the problem is (1 paragraph)
- What CliniqAI does (1 paragraph)
- How to run it locally (exact commands)
- Architecture diagram image
- Which Google Cloud + MongoDB tools you used and why
- A "Google-native hero moments" section covering: multilingual handwriting extraction, ADK agentic reasoning, tool orchestration, and real-time risk alerting
- Link to demo video

---

## What Judges Will Score You On

| Criterion | How CliniqAI Scores | Score |
|---|---|---|
| Technological Implementation | Google-native stack: Gemini on Vertex AI + ADK orchestration + Cloud Run deployment + Cloud Storage ingestion + MongoDB MCP memory/search | Very High |
| Design | Clean HTML + Tailwind UI. Sidebar navigation, patient cards, unmissable red alert box. Looks like a real product, not a student project | Very High |
| Potential Impact | 700,000 clinics in India. Real lives at risk from paper records. Real money saved from duplicate tests | Very High |
| Quality of Idea | No one else will build for Indian small clinics. Unique domain, unique user, unique problem | Very High |

---

## What Makes This Win Against 10,000 People

**Most people will build:** A chatbot that answers questions about MongoDB. A code generator. A personal productivity tool.

**You are building:** A system that could prevent a patient death by catching a drug conflict that a busy doctor missed at 10pm after seeing 80 patients.

That story — that stakes — is something a judge remembers when they write down their scores.

Three things that no competitor will have:
1. **Real human stakes** — not productivity, but safety
2. **India-specific context** — you can speak to this authentically from Mumbai
3. **Multimodal Gemini use** — reading handwritten Hindi/English prescriptions with vision AI is technically impressive and visually dramatic in a demo

---

## The 10-Day Calendar

| Day | Goal | Hours Needed |
|---|---|---|
| Day 1 | Setup: GCP account, Atlas, Node, Python, all installs | 3 hrs |
| Day 2 | Write vision_tool.py, test it on 3 sample images | 4 hrs |
| Day 3 | Connect MongoDB MCP server, test insert/find manually | 3 hrs |
| Day 4 | Write the main ADK agent, connect all tools | 4 hrs |
| Day 5 | Write alert_tool.py, test allergy detection | 3 hrs |
| Day 6 | Write `ui/index.html` (HTML + Tailwind), connect to agent via FastAPI | 4 hrs |
| Day 7 | End-to-end testing of all 5 test scenarios | 3 hrs |
| Day 8 | Deploy to Cloud Run, get live URL | 2 hrs |
| Day 9 | Bug fixes, polish UI, write README | 3 hrs |
| Day 10 | Record demo video, fill Devpost form, submit | 3 hrs |

**Total: ~32 hours. 10 days. One submission.**

---

## Submission Checklist (Do Not Skip Any)

- [ ] Hosted project URL (your Cloud Run URL)
- [ ] Public GitHub repo with MIT License visible in About section
- [ ] 3-minute demo video (upload to YouTube, set to Public or Unlisted)
- [ ] Devpost submission form filled with: project name, description, which track (MongoDB), which Google Cloud + partner tools used
- [ ] Submitted before June 11, 2026 at 2:00 PM PDT (= June 12, 2026 at 3:30 AM IST — submit by midnight June 11 IST to be safe)

---

*Built for the Google Cloud Rapid Agent Hackathon | MongoDB Track | May 2026*
