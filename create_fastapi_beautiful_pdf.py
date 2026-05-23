"""
Create a beautiful PDF with:
1. FastAPI basics and syntax
2. How FastAPI works
3. server.py explained using FastAPI concepts
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable
)

# ─── Colors ─────────────────────────────────────────────────────────────────
DARK = HexColor("#0f172a")
EMERALD = HexColor("#059669")
EMERALD_LT = HexColor("#d1fae5")
BLUE = HexColor("#2563eb")
BLUE_LT = HexColor("#dbeafe")
RED = HexColor("#dc2626")
RED_LT = HexColor("#fee2e2")
AMBER = HexColor("#d97706")
AMBER_LT = HexColor("#fef3c7")
PURPLE = HexColor("#7c3aed")
PURPLE_LT = HexColor("#ede9fe")
GRAY_BG = HexColor("#f8fafc")
GRAY_BORDER = HexColor("#e2e8f0")
GRAY_TEXT = HexColor("#64748b")
CODE_BG = HexColor("#1e293b")
CODE_FG = HexColor("#e2e8f0")

PAGE_W, PAGE_H = A4
MARGIN = 1.5 * cm

# ─── Styles ─────────────────────────────────────────────────────────────────
def S(name, **kw):
    return ParagraphStyle(name, **kw)

TITLE = S("title",
    fontSize=28, textColor=DARK, spaceAfter=6,
    fontName="Helvetica-Bold", alignment=TA_CENTER)

SUBTITLE = S("subtitle",
    fontSize=12, textColor=GRAY_TEXT, spaceAfter=2,
    fontName="Helvetica", alignment=TA_CENTER)

H1 = S("h1",
    fontSize=18, textColor=DARK, spaceBefore=16, spaceAfter=8,
    fontName="Helvetica-Bold")

H2 = S("h2",
    fontSize=14, textColor=EMERALD, spaceBefore=12, spaceAfter=6,
    fontName="Helvetica-Bold")

H3 = S("h3",
    fontSize=12, textColor=DARK, spaceBefore=10, spaceAfter=5,
    fontName="Helvetica-Bold")

BODY = S("body",
    fontSize=10, textColor=DARK, spaceAfter=6,
    fontName="Helvetica", leading=16, alignment=TA_JUSTIFY)

BODY_SMALL = S("body_small",
    fontSize=9, textColor=GRAY_TEXT, spaceAfter=4,
    fontName="Helvetica", leading=14)

CODE = S("code",
    fontSize=8.5, textColor=CODE_FG, spaceAfter=4,
    fontName="Courier", leading=12, backColor=CODE_BG,
    leftIndent=6, rightIndent=6)

LABEL_STORY = S("label_story",
    fontSize=10, textColor=EMERALD, fontName="Helvetica-Bold",
    spaceBefore=8, spaceAfter=3)

LABEL_TECH = S("label_tech",
    fontSize=10, textColor=BLUE, fontName="Helvetica-Bold",
    spaceBefore=8, spaceAfter=3)

LABEL_EXAMPLE = S("label_example",
    fontSize=10, textColor=RED, fontName="Helvetica-Bold",
    spaceBefore=8, spaceAfter=3)

BULLET = S("bullet",
    fontSize=10, textColor=DARK, spaceAfter=4,
    fontName="Helvetica", leading=14, leftIndent=16, bulletIndent=6)

# ─── Helper Functions ───────────────────────────────────────────────────────
def p(text, style=None):
    return Paragraph(text, style or BODY)

def sp(n=8):
    return Spacer(1, n)

def hr(color=GRAY_BORDER, thickness=0.5):
    return HRFlowable(width="100%", thickness=thickness, color=color, spaceAfter=8)

def colored_box(content, bg_color, border_color, title=None):
    """Create a colored box with optional title"""
    if title:
        title_para = Paragraph(title, S("box_title", fontSize=10, 
                                       fontName="Helvetica-Bold", 
                                       textColor=border_color, spaceAfter=6))
        content_list = [title_para] + (content if isinstance(content, list) else [content])
    else:
        content_list = content if isinstance(content, list) else [content]
    
    t = Table([[content_list]], colWidths=[PAGE_W - MARGIN*2 - 0.4*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), bg_color),
        ("BOX", (0,0), (-1,-1), 1.2, border_color),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
        ("RIGHTPADDING", (0,0), (-1,-1), 12),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ]))
    return t

def code_box(code_text):
    code_text = code_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return colored_box([p(code_text, CODE)], CODE_BG, CODE_BG)

def story_box(text):
    return colored_box([p(text, BODY)], EMERALD_LT, EMERALD)

def tech_box(content):
    if isinstance(content, str):
        content = [p(content, BODY)]
    return colored_box(content, BLUE_LT, BLUE)

def example_box(content):
    if isinstance(content, str):
        content = [p(content, BODY)]
    return colored_box(content, RED_LT, RED)

def concept_section(title, story_text, tech_content, example_content):
    """Create a complete concept section with 3 layers"""
    elems = [
        p(title, H2),
        sp(6),
        p("🎯 LAYER 1 — The Story", LABEL_STORY),
        story_box(story_text),
        sp(8),
        p("⚙️ LAYER 2 — Technical", LABEL_TECH),
        tech_box(tech_content),
        sp(8),
        p("💡 LAYER 3 — Example", LABEL_EXAMPLE),
        example_box(example_content),
        sp(10),
    ]
    return elems

# ─── Build PDF ──────────────────────────────────────────────────────────────
def build():
    doc = SimpleDocTemplate(
        "PHASE_1_COMPLETE_GUIDE.pdf",
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
        title="CliniqAI Phase 1 — Complete Guide",
        author="CliniqAI Learning Guide",
    )

    elems = []

    # ── COVER ────────────────────────────────────────────────────────────────
    elems += [
        sp(50),
        p("CliniqAI Phase 1", TITLE),
        p("Complete Guide: FastAPI + Server Logic", SUBTITLE),
        sp(4),
        hr(EMERALD, 2),
        sp(20),
        p("Learn FastAPI from zero", S("cov", fontSize=11, textColor=EMERALD, 
                                       alignment=TA_CENTER, fontName="Helvetica-Bold")),
        p("Understand server.py line by line", S("cov", fontSize=11, textColor=BLUE, 
                                         alignment=TA_CENTER, fontName="Helvetica-Bold")),
        p("See real examples in action", S("cov", fontSize=11, textColor=RED, 
                                       alignment=TA_CENTER, fontName="Helvetica-Bold")),
        sp(60),
        p("Google Cloud Rapid Agent Hackathon · May 2026",
          S("cov", fontSize=9, textColor=GRAY_TEXT, alignment=TA_CENTER, fontName="Helvetica")),
    ]

    # ── PART 0: FASTAPI BASICS ───────────────────────────────────────────────
    elems += [
        PageBreak(),
        p("PART 0: FastAPI Basics", H1),
        p("Everything you need to know to understand server.py", BODY_SMALL),
        sp(6),
        hr(PURPLE, 2),
    ]

    # Concept: What is FastAPI?
    elems += concept_section(
        "What is FastAPI?",
        "Imagine a receptionist at a clinic. Doctors walk up and say 'I have a photo' or 'show me Ramesh's history'. The receptionist understands them, does the work, and hands back an answer. FastAPI is that receptionist — it listens for requests from the outside world and routes them to the right function.",
        [
            p("<b>FastAPI is a Python web framework that:</b>", BODY),
            p("• Listens for HTTP requests (GET, POST, etc.)", BULLET),
            p("• Routes requests to the right function", BULLET),
            p("• Validates incoming data automatically", BULLET),
            p("• Returns JSON responses", BULLET),
            p("• Generates interactive API documentation", BULLET),
            sp(4),
            p("<b>Why FastAPI over Flask or Django?</b>", BODY),
            p("• <b>Async support:</b> Handle multiple requests at the same time", BULLET),
            p("• <b>Auto validation:</b> Pydantic checks data types automatically", BULLET),
            p("• <b>Auto docs:</b> /docs page generated automatically", BULLET),
            p("• <b>Fast:</b> One of the fastest Python frameworks", BULLET),
        ],
        [
            p("<b>Basic structure:</b>", BODY_SMALL),
            code_box('''from fastapi import FastAPI

app = FastAPI()

@app.get("/hello")
def hello():
    return {"message": "Hello, World!"}

# Run with: uvicorn main:app --reload'''),
        ]
    )
    elems += elems[-3:]
    elems = elems[:-3]

    # Concept: HTTP Methods
    elems += concept_section(
        "HTTP Methods: GET vs POST",
        "GET is like asking a librarian 'show me books about Python'. POST is like handing the librarian a form and saying 'store this information for me'. GET retrieves data. POST sends data.",
        [
            p("<b>GET:</b> Retrieve data (no body)", BODY),
            code_box('''@app.get("/patients")
def get_patients():
    return {"patients": [...]}

# Call with: GET http://localhost:8000/patients'''),
            sp(6),
            p("<b>POST:</b> Send data (with body)", BODY),
            code_box('''@app.post("/process")
def process_image(file: UploadFile):
    return {"status": "processed"}

# Call with: POST http://localhost:8000/process
# With file attachment in body'''),
        ],
        [
            p("<b>Real examples from CliniqAI:</b>", BODY_SMALL),
            code_box('''GET /health
→ Returns: {"status": "running", "mongodb": "connected"}

POST /process
→ Accepts: Image file
→ Returns: {"patient": {...}, "alerts": [...]}

POST /query
→ Accepts: {"query": "how many patients"}
→ Returns: {"answer": "Total patients: 5"}'''),
        ]
    )
    elems += elems[-3:]
    elems = elems[:-3]

    # Concept: Decorators
    elems += concept_section(
        "Decorators: @app.get() and @app.post()",
        "A decorator is like a label on a mailbox. @app.get('/health') says 'when someone sends a GET request to /health, run this function'. The @ symbol is Python syntax for decorators.",
        [
            p("<b>Decorator syntax:</b>", BODY),
            code_box('''@app.get("/endpoint")
def function_name():
    return {"data": "here"}

# The @ symbol means: 'apply this decorator'
# app.get() is the decorator
# It tells FastAPI: 'when GET /endpoint, run function_name'
# The function name doesn't matter — the path does'''),
            sp(6),
            p("<b>Multiple decorators on same function:</b>", BODY),
            code_box('''@app.get("/patients")
@app.get("/get-patients")  # Both URLs work!
def get_patients():
    return {"patients": [...]}'''),
        ],
        [
            p("<b>From server.py:</b>", BODY_SMALL),
            code_box('''@app.get("/health")
def health():
    return {"status": "running"}

@app.post("/process")
async def process_document(file: UploadFile):
    return {"result": "..."}

@app.post("/query")
async def run_query(request: QueryRequest):
    return {"answer": "..."}'''),
        ]
    )
    elems += elems[-3:]
    elems = elems[:-3]

    # Concept: Request and Response
    elems += concept_section(
        "Request and Response Flow",
        "A request is what the client sends. A response is what the server sends back. FastAPI automatically converts Python dictionaries to JSON.",
        [
            p("<b>Request → Function → Response</b>", BODY),
            code_box('''# Client sends:
POST /query
{"query": "how many patients"}

# FastAPI receives and converts to Python:
request = QueryRequest(query="how many patients")

# Function processes:
def run_query(request: QueryRequest):
    answer = f"Total: {count_patients()}"
    return {"answer": answer}

# FastAPI converts back to JSON and sends:
{"answer": "Total: 5"}'''),
            sp(6),
            p("<b>Data validation with Pydantic:</b>", BODY),
            code_box('''from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str

# If client sends: {"query": "hello"}
# FastAPI accepts ✓

# If client sends: {"query": 123}
# FastAPI rejects ✗ (query must be string)

# If client sends: {"wrong_field": "hello"}
# FastAPI rejects ✗ (missing required field)'''),
        ],
        [
            p("<b>Example from CliniqAI:</b>", BODY_SMALL),
            code_box('''Client sends:
POST /query
{"query": "how many patients"}

FastAPI validates:
✓ Is "query" a string? YES
✓ Is "query" present? YES

Calls function:
run_query(request=QueryRequest(query="how many patients"))

Function returns:
{"answer": "Total patients: 5"}

Client receives:
{"answer": "Total patients: 5"}'''),
        ]
    )
    elems += elems[-3:]
    elems = elems[:-3]

    # Concept: Async
    elems += concept_section(
        "Async: Handle Multiple Requests",
        "Imagine a restaurant. A synchronous waiter serves one table, waits for them to finish, then serves the next table. An async waiter takes an order from table 1, moves to table 2 while table 1's food is cooking, takes their order, and so on. Async means 'don't wait for slow operations'.",
        [
            p("<b>Sync (blocking):</b>", BODY),
            code_box('''@app.post("/process")
def process_image(file: UploadFile):
    image_bytes = file.read()  # WAIT for file to load
    result = gemini_api_call(image_bytes)  # WAIT for API
    return result

# If API takes 5 seconds, user waits 5 seconds
# Other requests are blocked!'''),
            sp(6),
            p("<b>Async (non-blocking):</b>", BODY),
            code_box('''@app.post("/process")
async def process_image(file: UploadFile):
    image_bytes = await file.read()  # Don't wait, continue
    result = await gemini_api_call(image_bytes)  # Don't wait
    return result

# If API takes 5 seconds, FastAPI handles other requests!
# Multiple users can upload simultaneously'''),
        ],
        [
            p("<b>In CliniqAI:</b>", BODY_SMALL),
            code_box('''@app.post("/process")
async def process_document(file: UploadFile = File(...)):
    # async = this function can run concurrently
    # Multiple doctors can upload images at same time
    
    image_bytes = await file.read()
    # await = wait for file to load, but don't block others
    
    extracted = extract_from_prescription(image_bytes)
    # This is fast (just calls our function)
    
    return {...}'''),
        ]
    )
    elems += elems[-3:]
    elems = elems[:-3]

    # ── PART 1: SERVER.PY EXPLAINED ──────────────────────────────────────────
    elems += [
        PageBreak(),
        p("PART 1: server.py Explained", H1),
        p("Using FastAPI concepts to understand the code", BODY_SMALL),
        sp(6),
        hr(BLUE, 2),
    ]

    # Section: Imports
    elems += [
        p("Section 1: Imports", H2),
        sp(4),
    ]

    imports_table = [
        ["Import", "What it does", "Why we use it"],
        ["os", "Access environment variables", "Read API keys from .env"],
        ["re", "Regular expressions", "Escape special chars in queries"],
        ["uuid", "Generate unique IDs", "Create unique patient IDs"],
        ["datetime, date", "Date/time handling", "Record visit dates"],
        ["FastAPI", "Web framework", "Create the server"],
        ["UploadFile, File", "File upload handling", "Accept image uploads"],
        ["CORSMiddleware", "Cross-Origin requests", "Allow frontend to call backend"],
        ["BaseModel", "Data validation", "Validate incoming JSON"],
        ["MongoClient", "MongoDB connection", "Connect to database"],
        ["load_dotenv", "Load .env file", "Read API keys"],
    ]

    imports_t = Table(imports_table, colWidths=[2.5*cm, 3.5*cm, 3.5*cm])
    imports_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, GRAY_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, GRAY_BG]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    elems.append(imports_t)
    elems.append(sp(10))

    # Section: App Setup
    elems += concept_section(
        "Section 2: Creating the FastAPI App",
        "We create one FastAPI app object. All endpoints are attached to this object. It's like creating a restaurant, then adding different counters (endpoints) to it.",
        [
            code_box('''app = FastAPI(title="CliniqAI", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)'''),
            sp(6),
            p("<b>What this does:</b>", BODY),
            p("• <b>FastAPI()</b> — Create the app", BULLET),
            p("• <b>title, version</b> — Shown in /docs page", BULLET),
            p("• <b>CORSMiddleware</b> — Allow requests from any frontend", BULLET),
            p("• <b>allow_origins=['*']</b> — Accept requests from anywhere", BULLET),
        ],
        [
            p("<b>Why CORS?</b>", BODY_SMALL),
            code_box('''Without CORS:
Frontend at localhost:3000 tries to call localhost:8000
Browser blocks it! ✗

With CORS:
Frontend at localhost:3000 can call localhost:8000
Browser allows it! ✓'''),
        ]
    )
    elems += elems[-3:]
    elems = elems[:-3]

    # Section: Request Models
    elems += concept_section(
        "Section 3: Pydantic Models (Data Validation)",
        "A Pydantic model is a blueprint for incoming data. It says 'I expect a JSON object with these fields and these types'. FastAPI automatically validates and rejects bad data.",
        [
            code_box('''from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str

# This means:
# - Expect a JSON object
# - Must have a "query" field
# - "query" must be a string
# - Nothing else is allowed'''),
            sp(6),
            p("<b>Validation examples:</b>", BODY),
            code_box('''# ✓ ACCEPTED
{"query": "how many patients"}

# ✗ REJECTED (query is number, not string)
{"query": 123}

# ✗ REJECTED (missing required field)
{"name": "Ramesh"}

# ✗ REJECTED (extra field)
{"query": "hello", "extra": "field"}'''),
        ],
        [
            p("<b>In server.py:</b>", BODY_SMALL),
            code_box('''@app.post("/query")
async def run_query(request: QueryRequest):
    # FastAPI automatically:
    # 1. Receives JSON
    # 2. Validates it matches QueryRequest
    # 3. Converts to Python object
    # 4. Passes to function
    
    query = request.query  # Access the field
    return {"answer": "..."}'''),
        ]
    )
    elems += elems[-3:]
    elems = elems[:-3]

    # Section: Health Endpoint
    elems += concept_section(
        "Section 4: /health Endpoint",
        "The health endpoint is like a heartbeat check. Clients call it to see if the server is alive and if MongoDB is connected.",
        [
            code_box('''@app.get("/health")
def health():
    db_connected = get_db()
    
    if db_connected:
        mongo_status = "connected"
    else:
        mongo_status = "not configured (using in-memory store)"
    
    return {
        "status": "running",
        "mongodb": mongo_status,
        "google_api_key_set": bool(GOOGLE_API_KEY and "your_google" not in GOOGLE_API_KEY),
    }'''),
            sp(6),
            p("<b>Line by line:</b>", BODY),
            p("• <b>@app.get('/health')</b> — Create GET endpoint", BULLET),
            p("• <b>def health()</b> — Function name (doesn't matter)", BULLET),
            p("• <b>get_db()</b> — Try to connect to MongoDB", BULLET),
            p("• <b>return {...}</b> — Return JSON response", BULLET),
        ],
        [
            p("<b>Example request/response:</b>", BODY_SMALL),
            code_box('''REQUEST:
GET http://localhost:8000/health

RESPONSE:
{
  "status": "running",
  "mongodb": "not configured (using in-memory store)",
  "google_api_key_set": false
}'''),
        ]
    )
    elems += elems[-3:]
    elems = elems[:-3]

    # Section: Process Endpoint
    elems += concept_section(
        "Section 5: /process Endpoint (The Main One)",
        "This is the heart of CliniqAI. It receives an image, extracts patient data, checks for drug conflicts, and stores everything.",
        [
            code_box('''@app.post("/process")
async def process_document(file: UploadFile = File(...)):
    # Step 1: Read image
    image_bytes = await file.read()
    
    # Step 2: Extract data with Gemini
    extracted = extract_from_prescription(image_bytes)
    
    # Step 3: Check if patient exists
    patient_name = extracted.get("patient_name", "Unknown")
    existing_patient = find_patient_in_db(patient_name)
    
    # Step 4: Store or update
    if existing_patient:
        update_patient(existing_patient, extracted)
    else:
        insert_new_patient(extracted)
    
    # Step 5: Check drug conflicts
    alerts = check_drug_conflicts(...)
    
    # Step 6: Return result
    return {"patient": {...}, "alerts": alerts}'''),
            sp(6),
            p("<b>Key parameters:</b>", BODY),
            p("• <b>file: UploadFile</b> — The uploaded image", BULLET),
            p("• <b>= File(...)</b> — This is required (... means 'required')", BULLET),
            p("• <b>async</b> — Handle multiple uploads simultaneously", BULLET),
            p("• <b>await file.read()</b> — Wait for file to load", BULLET),
        ],
        [
            p("<b>Example request/response:</b>", BODY_SMALL),
            code_box('''REQUEST:
POST http://localhost:8000/process
[Image file attached]

RESPONSE:
{
  "record_id": "507f1f77bcf86cd799439011",
  "is_returning": false,
  "patient": {
    "name": "Ramesh Gupta",
    "age": 45,
    "medicines": [...]
  },
  "alerts": [
    {
      "severity": "HIGH",
      "type": "ALLERGY",
      "message": "..."
    }
  ]
}'''),
        ]
    )
    elems += elems[-3:]
    elems = elems[:-3]

    # Section: Query Endpoint
    elems += concept_section(
        "Section 6: /query Endpoint",
        "This endpoint accepts natural language questions and returns answers. For Phase 1, it does simple keyword matching.",
        [
            code_box('''@app.post("/query")
async def run_query(request: QueryRequest):
    query = request.query.lower()
    
    if "how many" in query or "count" in query:
        count = count_patients()
        return {"answer": f"Total patients: {count}"}
    
    elif "diabetic" in query or "diabetes" in query:
        patients = find_patients_with("diabetes")
        return {"answer": f"Found {len(patients)} diabetic patients"}
    
    else:
        # Search by medicine, condition, or name
        results = search_patients(query)
        return {"answer": f"Found {len(results)} result(s)"}'''),
            sp(6),
            p("<b>How it works:</b>", BODY),
            p("• <b>request: QueryRequest</b> — Receives validated JSON", BULLET),
            p("• <b>query.lower()</b> — Convert to lowercase for matching", BULLET),
            p("• <b>if 'how many' in query</b> — Simple keyword matching", BULLET),
            p("• <b>return {'answer': ...}</b> — Return natural language response", BULLET),
        ],
        [
            p("<b>Example requests/responses:</b>", BODY_SMALL),
            code_box('''REQUEST 1:
POST /query
{"query": "how many patients"}

RESPONSE:
{"answer": "Total patients: 5"}

---

REQUEST 2:
POST /query
{"query": "metformin"}

RESPONSE:
{"answer": "Found 2 result(s): Ramesh Gupta, Sunita Devi"}'''),
        ]
    )
    elems += elems[-3:]
    elems = elems[:-3]

    # ── FOOTER ───────────────────────────────────────────────────────────────
    elems += [
        PageBreak(),
        sp(30),
        hr(GRAY_BORDER),
        p("CliniqAI Phase 1 Complete Guide · FastAPI + server.py",
          S("footer", fontSize=9, textColor=GRAY_TEXT, alignment=TA_CENTER, fontName="Helvetica")),
        p("Ready for Phase 2: Build the Web UI",
          S("next", fontSize=10, textColor=EMERALD, alignment=TA_CENTER,
            fontName="Helvetica-Bold", spaceBefore=4)),
    ]

    doc.build(elems)
    print("✓ Beautiful PDF created: PHASE_1_COMPLETE_GUIDE.pdf")

if __name__ == "__main__":
    build()
