"""
Generates CliniqAI_Phase_1_Learning.pdf

Follows the Master Learning Prompt rules:
- 3-layer teaching (story → technical → interview)
- Toptal interview boxes for every concept
- ASCII diagrams before complex explanations
- Why not the alternatives
- Bugs discovered & fixed (with before/after diffs)
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

# ─── Colours ────────────────────────────────────────────────────────────────
EMERALD     = HexColor("#059669")
EMERALD_LT  = HexColor("#d1fae5")
RED         = HexColor("#dc2626")
RED_LT      = HexColor("#fee2e2")
BLUE        = HexColor("#2563eb")
BLUE_LT     = HexColor("#dbeafe")
AMBER       = HexColor("#d97706")
AMBER_LT    = HexColor("#fef3c7")
GRAY_BG     = HexColor("#f8fafc")
GRAY_BORDER = HexColor("#e2e8f0")
GRAY_TEXT   = HexColor("#64748b")
DARK        = HexColor("#0f172a")
CODE_BG     = HexColor("#1e293b")
CODE_FG     = HexColor("#e2e8f0")

PAGE_W, PAGE_H = A4
MARGIN = 1.8 * cm

# ─── Styles ─────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

def S(name, **kw):
    return ParagraphStyle(name, **kw)

TITLE_STYLE = S("title",
    fontSize=26, textColor=DARK, spaceAfter=4,
    fontName="Helvetica-Bold", alignment=TA_CENTER)

SUBTITLE_STYLE = S("subtitle",
    fontSize=11, textColor=GRAY_TEXT, spaceAfter=2,
    fontName="Helvetica", alignment=TA_CENTER)

H1 = S("h1",
    fontSize=16, textColor=DARK, spaceBefore=18, spaceAfter=6,
    fontName="Helvetica-Bold")

H2 = S("h2",
    fontSize=13, textColor=EMERALD, spaceBefore=14, spaceAfter=5,
    fontName="Helvetica-Bold")

H3 = S("h3",
    fontSize=11, textColor=DARK, spaceBefore=10, spaceAfter=4,
    fontName="Helvetica-Bold")

BODY = S("body",
    fontSize=10, textColor=DARK, spaceAfter=5,
    fontName="Helvetica", leading=15)

BODY_SMALL = S("body_small",
    fontSize=9, textColor=GRAY_TEXT, spaceAfter=4,
    fontName="Helvetica", leading=13)

CODE_STYLE = S("code",
    fontSize=8.5, textColor=CODE_FG, spaceAfter=4,
    fontName="Courier", leading=13, backColor=CODE_BG,
    leftIndent=8, rightIndent=8)

LABEL_EMERALD = S("label_green",
    fontSize=9, textColor=EMERALD, fontName="Helvetica-Bold",
    spaceBefore=6, spaceAfter=2)

LABEL_RED = S("label_red",
    fontSize=9, textColor=RED, fontName="Helvetica-Bold",
    spaceBefore=6, spaceAfter=2)

LABEL_BLUE = S("label_blue",
    fontSize=9, textColor=BLUE, fontName="Helvetica-Bold",
    spaceBefore=6, spaceAfter=2)

LABEL_AMBER = S("label_amber",
    fontSize=9, textColor=AMBER, fontName="Helvetica-Bold",
    spaceBefore=6, spaceAfter=2)

BULLET = S("bullet",
    fontSize=10, textColor=DARK, spaceAfter=3,
    fontName="Helvetica", leading=14, leftIndent=14, bulletIndent=4)

# ─── Helper: coloured box ───────────────────────────────────────────────────
def box(paragraphs, bg, border):
    t = Table([[paragraphs]], colWidths=[PAGE_W - MARGIN*2 - 0.4*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), bg),
        ("BOX",        (0,0), (-1,-1), 0.8, border),
        ("LEFTPADDING",  (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING",   (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0), (-1,-1), 8),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return t

def tworow_table(rows, col_widths=None):
    """Renders a 2-column key-value style table."""
    if not col_widths:
        col_widths = [5*cm, PAGE_W - MARGIN*2 - 5*cm - 0.4*cm]
    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (0,-1), GRAY_BG),
        ("BACKGROUND",   (1,0), (1,-1), white),
        ("BOX",          (0,0), (-1,-1), 0.5, GRAY_BORDER),
        ("INNERGRID",    (0,0), (-1,-1), 0.3, GRAY_BORDER),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING",   (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0), (-1,-1), 6),
        ("FONTNAME",     (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,-1), 9),
        ("TEXTCOLOR",    (0,0), (0,-1), GRAY_TEXT),
        ("VALIGN",       (0,0), (-1,-1), "TOP"),
    ]))
    return t

def p(text, style=None):
    return Paragraph(text, style or BODY)

def sp(n=6):
    return Spacer(1, n)

def hr():
    return HRFlowable(width="100%", thickness=0.5, color=GRAY_BORDER, spaceAfter=6)

# ─── Build document ──────────────────────────────────────────────────────────
def build():
    doc = SimpleDocTemplate(
        "CliniqAI_Phase_1_Learning.pdf",
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN,  bottomMargin=MARGIN,
        title="CliniqAI Phase 1 Learning",
        author="CliniqAI Build Guide",
    )

    elems = []

    # ── COVER ────────────────────────────────────────────────────────────────
    elems += [
        sp(40),
        p("CliniqAI", TITLE_STYLE),
        p("Phase 1 — Core Agent &amp; Drug Alert System", SUBTITLE_STYLE),
        p("Build · Learn · Win Toptal", SUBTITLE_STYLE),
        sp(6),
        hr(),
        sp(4),
        p("Google Cloud Rapid Agent Hackathon · MongoDB Track · May 2026",
          S("cov", fontSize=9, textColor=GRAY_TEXT, alignment=TA_CENTER, fontName="Helvetica")),
        sp(60),
    ]

    # ── SECTION 1: WHAT WE BUILT ─────────────────────────────────────────────
    elems += [hr(), p("1 — What We Built in Phase 1", H1)]

    elems.append(p(
        "Phase 1 is the <b>engine</b> of CliniqAI. No UI yet — just the three files that do "
        "all the real work: read a prescription photo, check for drug conflicts, and store "
        "everything in MongoDB.", BODY))

    elems.append(box([
        p("Files created in Phase 1", S("bh", fontSize=9, fontName="Helvetica-Bold",
          textColor=GRAY_TEXT, spaceAfter=4)),
        p("<font name='Courier' size='9'>cliniqai/</font>", BODY_SMALL),
        p("<font name='Courier' size='9'>├── agent/</font>", BODY_SMALL),
        p("<font name='Courier' size='9'>│   ├── __init__.py         ← makes 'agent' a Python package</font>", BODY_SMALL),
        p("<font name='Courier' size='9'>│   ├── server.py           ← FastAPI backend (the brain)</font>", BODY_SMALL),
        p("<font name='Courier' size='9'>│   └── tools/</font>", BODY_SMALL),
        p("<font name='Courier' size='9'>│       ├── __init__.py</font>", BODY_SMALL),
        p("<font name='Courier' size='9'>│       ├── vision_tool.py  ← reads prescription photos</font>", BODY_SMALL),
        p("<font name='Courier' size='9'>│       └── alert_tool.py   ← catches drug conflicts</font>", BODY_SMALL),
        p("<font name='Courier' size='9'>├── .env                    ← secret keys (never commit!)</font>", BODY_SMALL),
        p("<font name='Courier' size='9'>├── requirements.txt        ← Python dependencies</font>", BODY_SMALL),
        p("<font name='Courier' size='9'>└── test_app.py             ← 7 automated tests</font>", BODY_SMALL),
    ], GRAY_BG, GRAY_BORDER))

    elems.append(sp())

    # ── SECTION 2: THE FLOW ──────────────────────────────────────────────────
    elems += [hr(), p("2 — How It All Connects (ASCII Diagram)", H1)]

    elems.append(p("Before any code — here is the complete flow from photo upload to alert:", BODY))

    elems.append(box([
        p("<font name='Courier' size='8.5' color='#e2e8f0'>Doctor uploads photo</font>", BODY_SMALL),
        p("<font name='Courier' size='8.5' color='#e2e8f0'>        |</font>", BODY_SMALL),
        p("<font name='Courier' size='8.5' color='#e2e8f0'>        ▼</font>", BODY_SMALL),
        p("<font name='Courier' size='8.5' color='#e2e8f0'>POST /process  (server.py)</font>", BODY_SMALL),
        p("<font name='Courier' size='8.5' color='#e2e8f0'>        |</font>", BODY_SMALL),
        p("<font name='Courier' size='8.5' color='#e2e8f0'>        ▼</font>", BODY_SMALL),
        p("<font name='Courier' size='8.5' color='#e2e8f0'>vision_tool.py  →  Gemini reads image  →  returns JSON</font>", BODY_SMALL),
        p("<font name='Courier' size='8.5' color='#e2e8f0'>        |</font>", BODY_SMALL),
        p("<font name='Courier' size='8.5' color='#e2e8f0'>        ▼</font>", BODY_SMALL),
        p("<font name='Courier' size='8.5' color='#e2e8f0'>MongoDB: patient exists?</font>", BODY_SMALL),
        p("<font name='Courier' size='8.5' color='#e2e8f0'>   YES → update_one (push new visit)</font>", BODY_SMALL),
        p("<font name='Courier' size='8.5' color='#e2e8f0'>   NO  → insert_one (new patient doc)</font>", BODY_SMALL),
        p("<font name='Courier' size='8.5' color='#e2e8f0'>        |</font>", BODY_SMALL),
        p("<font name='Courier' size='8.5' color='#e2e8f0'>        ▼</font>", BODY_SMALL),
        p("<font name='Courier' size='8.5' color='#e2e8f0'>alert_tool.py</font>", BODY_SMALL),
        p("<font name='Courier' size='8.5' color='#e2e8f0'>   Layer 1: Direct allergy check</font>", BODY_SMALL),
        p("<font name='Courier' size='8.5' color='#e2e8f0'>   Layer 2: Cross-allergy check</font>", BODY_SMALL),
        p("<font name='Courier' size='8.5' color='#e2e8f0'>   Layer 3: Drug-drug interaction check</font>", BODY_SMALL),
        p("<font name='Courier' size='8.5' color='#e2e8f0'>        |</font>", BODY_SMALL),
        p("<font name='Courier' size='8.5' color='#e2e8f0'>        ▼</font>", BODY_SMALL),
        p("<font name='Courier' size='8.5' color='#e2e8f0'>Return JSON to frontend: {patient, alerts, is_returning}</font>", BODY_SMALL),
    ], CODE_BG, CODE_BG))

    # ── SECTION 3: CONCEPTS ──────────────────────────────────────────────────
    elems += [hr(), p("3 — Concepts (3-Layer Teaching)", H1)]

    # ── Concept A: FastAPI ──
    elems += [p("Concept A — FastAPI", H2)]

    elems.append(p("LAYER 1 — The Story", LABEL_EMERALD))
    elems.append(box([p(
        "Imagine a reception desk at a clinic. Doctors walk up and say "
        "<i>'I have a photo'</i> or <i>'show me Ramesh's history'</i>. The receptionist "
        "understands them, does the work, and hands back an answer. FastAPI is that "
        "receptionist — it listens for requests from the outside world and routes them "
        "to the right function.", BODY)], EMERALD_LT, EMERALD))

    elems.append(p("LAYER 2 — Technical", LABEL_BLUE))
    elems.append(box([
        p("FastAPI is a Python web framework. You write a function and decorate it with "
          "<font name='Courier'>@app.post('/process')</font> — FastAPI automatically makes it "
          "available at that URL. It also generates interactive API docs at "
          "<font name='Courier'>/docs</font> automatically.", BODY),
        p("<b>Key endpoints we built:</b>", BODY),
        p("• <font name='Courier'>GET /health</font> — Is the server alive? Is MongoDB connected?", BULLET),
        p("• <font name='Courier'>POST /process</font> — Upload image → extract → store → check alerts", BULLET),
        p("• <font name='Courier'>POST /query</font> — Natural language search", BULLET),
        p("• <font name='Courier'>GET /recent</font> — Last 10 patients", BULLET),
        p("• <font name='Courier'>POST /test/process</font> — Test flow without Gemini API", BULLET),
    ], BLUE_LT, BLUE))

    elems.append(p("LAYER 3 — Toptal Interview", LABEL_RED))
    elems.append(box([
        p("<b>Q:</b> Why FastAPI over Flask or Django?", BODY),
        p("<b>A:</b> FastAPI has three advantages for CliniqAI: (1) async support — image "
          "processing and MongoDB calls can run concurrently; (2) automatic type validation via "
          "Pydantic — if someone POSTs the wrong JSON shape, FastAPI rejects it before my code "
          "even runs; (3) auto-generated /docs page — critical for demo. Flask has none of these "
          "by default. Django is too heavy for a single-purpose API.", BODY),
        p("<b>FOLLOW-UP:</b> What's the trade-off of FastAPI?", BODY),
        p("<b>FOLLOW-UP ANSWER:</b> Steeper learning curve than Flask for pure beginners. "
          "Also, it's ASGI-only — you need an ASGI server like uvicorn, not the classic "
          "gunicorn. In Cloud Run that's fine — we just run uvicorn.", BODY),
    ], RED_LT, RED))

    elems.append(sp())

    # ── Concept B: vision_tool ──
    elems += [p("Concept B — vision_tool.py (Gemini Vision)", H2)]

    elems.append(p("LAYER 1 — The Story", LABEL_EMERALD))
    elems.append(box([p(
        "Imagine hiring a medical secretary who speaks both Hindi and English, "
        "can read any doctor's handwriting (even the bad kind), and always fills in "
        "a standard form with the same fields every time. That is Gemini Vision. "
        "You give it a photo, it gives you clean structured data.", BODY)], EMERALD_LT, EMERALD))

    elems.append(p("LAYER 2 — Technical", LABEL_BLUE))
    elems.append(box([
        p("We send the image bytes + a structured prompt to Gemini's "
          "<font name='Courier'>generate_content()</font> method. The prompt tells Gemini to "
          "return <b>only</b> a JSON object — no extra words. Gemini sometimes wraps the JSON "
          "in markdown code blocks, so we strip those before parsing.", BODY),
        p("<b>The prompt trick:</b>", BODY),
        p("• Tell Gemini: <i>'Return ONLY the JSON. No preamble, no explanation.'</i>", BULLET),
        p("• Strip <font name='Courier'>```json ... ```</font> markdown wrappers", BULLET),
        p("• Wrap <font name='Courier'>json.loads()</font> in try/except — LLMs sometimes add comments", BULLET),
    ], BLUE_LT, BLUE))

    elems.append(p("LAYER 3 — Toptal Interview", LABEL_RED))
    elems.append(box([
        p("<b>Q:</b> How do you ensure consistent structured output from an LLM?", BODY),
        p("<b>A:</b> Three techniques: (1) prompt engineering — 'Return ONLY valid JSON matching this schema'; "
          "(2) post-processing — strip markdown wrappers, handle edge cases; "
          "(3) fallback — if json.loads() fails, return an error dict with the raw text for debugging. "
          "For production, I'd use Gemini's structured output mode or Pydantic validation.", BODY),
        p("<b>FOLLOW-UP:</b> Why not use GPT-4V?", BODY),
        p("<b>FOLLOW-UP ANSWER:</b> For this hackathon: cost and credits. Gemini 2.0 Flash is free "
          "on GCP credits, handles Hindi handwriting well, and is the stack the hackathon is built around. "
          "GPT-4V costs $0.01 per image — at scale that matters.", BODY),
    ], RED_LT, RED))

    elems.append(sp())

    # ── Concept C: alert_tool ──
    elems += [p("Concept C — alert_tool.py (3-Layer Drug Checker)", H2)]

    elems.append(p("LAYER 1 — The Story", LABEL_EMERALD))
    elems.append(box([p(
        "Imagine a pharmacist who has memorised every drug family and every known interaction. "
        "A prescription arrives. Before handing over the medicine, they check three things: "
        "(1) Is the patient allergic to this drug family? "
        "(2) Even if not directly allergic — is there a related drug they react to? "
        "(3) Are two medicines in this bag known to be dangerous together? "
        "That is alert_tool.py.", BODY)], EMERALD_LT, EMERALD))

    elems.append(p("LAYER 2 — Technical", LABEL_BLUE))
    elems.append(box([
        p("Three independent checks run in sequence:", BODY),
        p("<b>Layer 1 — Direct allergy:</b> "
          "Patient has 'penicillin' allergy. New prescription has 'Amoxicillin'. "
          "Amoxicillin is in <font name='Courier'>ALLERGY_FAMILIES['penicillin']</font>. → HIGH alert.", BULLET),
        p("<b>Layer 2 — Cross-allergy:</b> "
          "Penicillin allergy has ~10% cross-reactivity with cephalosporins. "
          "New prescription has 'Cefixime'. → MEDIUM alert.", BULLET),
        p("<b>Layer 3 — Drug-drug interaction:</b> "
          "Patient currently on Warfarin. New prescription adds Aspirin. "
          "<font name='Courier'>DANGEROUS_COMBOS[('warfarin','aspirin')]</font> → HIGH alert.", BULLET),
        p("All alerts are sorted: HIGH first. Output is a dict with "
          "<font name='Courier'>has_alerts, alert_count, high_severity, alerts[]</font>.", BODY),
    ], BLUE_LT, BLUE))

    elems.append(p("LAYER 3 — Toptal Interview", LABEL_RED))
    elems.append(box([
        p("<b>Q:</b> Why rule-based instead of asking the LLM to check interactions?", BODY),
        p("<b>A:</b> Safety-critical systems must be deterministic. A known penicillin→amoxicillin "
          "allergy must trigger 100% of the time — not 97% of the time. LLMs are probabilistic. "
          "They can hallucinate. They can forget. A rule engine is a lookup table: it either matches or it doesn't. "
          "We use the LLM for extraction (where a near-miss is acceptable) and rules for safety (where it is not).", BODY),
        p("<b>FOLLOW-UP:</b> How would you scale the drug database?", BODY),
        p("<b>FOLLOW-UP ANSWER:</b> Replace the hardcoded dictionaries with a DrugBank or RxNorm API call. "
          "The function signature stays identical — callers don't change. This is the Open/Closed Principle: "
          "open for extension, closed for modification.", BODY),
    ], RED_LT, RED))

    elems.append(sp())

    # ── Concept D: MongoDB ──
    elems += [p("Concept D — MongoDB Patient Document Design", H2)]

    elems.append(p("LAYER 1 — The Story", LABEL_EMERALD))
    elems.append(box([p(
        "Imagine a physical file cabinet. Each patient has ONE folder. Inside that folder are "
        "ALL their visits — stacked on top of each other. One folder can have 2 pages, another "
        "can have 40. There's no fixed size. That is MongoDB. In SQL (like MySQL), you'd need "
        "a separate table for visits, joined with a patient ID. In MongoDB, one document = "
        "one patient = all their history in one place.", BODY)], EMERALD_LT, EMERALD))

    elems.append(p("LAYER 2 — Technical", LABEL_BLUE))
    elems.append(box([
        p("The patient document structure we use:", BODY),
        p("<font name='Courier' size='8'>{ '_id': ObjectId,</font>", BODY_SMALL),
        p("<font name='Courier' size='8'>  'patient_id': 'uuid-string',</font>", BODY_SMALL),
        p("<font name='Courier' size='8'>  'name': 'Ramesh Gupta',</font>", BODY_SMALL),
        p("<font name='Courier' size='8'>  'age': 45,</font>", BODY_SMALL),
        p("<font name='Courier' size='8'>  'known_allergies': ['penicillin'],</font>", BODY_SMALL),
        p("<font name='Courier' size='8'>  'conditions': ['Type 2 Diabetes'],</font>", BODY_SMALL),
        p("<font name='Courier' size='8'>  'visits': [</font>", BODY_SMALL),
        p("<font name='Courier' size='8'>    { 'date': '2026-05-16', 'doctor': 'Dr. Sharma',</font>", BODY_SMALL),
        p("<font name='Courier' size='8'>      'medicines': [{name, dose, frequency, duration}],</font>", BODY_SMALL),
        p("<font name='Courier' size='8'>      'tests': [], 'notes': '...' }</font>", BODY_SMALL),
        p("<font name='Courier' size='8'>  ] }</font>", BODY_SMALL),
        p("<b>Key MongoDB operations used:</b>", BODY),
        p("• <font name='Courier'>insert_one()</font> — new patient", BULLET),
        p("• <font name='Courier'>find_one({'name': name})</font> — check if returning", BULLET),
        p("• <font name='Courier'>update_one(..., {'$push': {'visits': visit}})</font> — add visit", BULLET),
        p("• <font name='Courier'>find({'conditions': {'$regex': ...}})</font> — search", BULLET),
    ], BLUE_LT, BLUE))

    elems.append(p("LAYER 3 — Toptal Interview", LABEL_RED))
    elems.append(box([
        p("<b>Q:</b> Why MongoDB over PostgreSQL for patient records?", BODY),
        p("<b>A:</b> Patient records are schema-flexible — one patient has 2 medicines, another has 8. "
          "The visits array grows over time with no fixed length. MongoDB's document model fits this naturally. "
          "The trade-off is weaker ACID guarantees — but for a clinic app where we're appending visits "
          "and not doing financial transactions, that's acceptable. For billing, I'd use PostgreSQL.", BODY),
        p("<b>FOLLOW-UP:</b> How does <font name='Courier'>$push</font> work?", BODY),
        p("<b>FOLLOW-UP ANSWER:</b> $push is a MongoDB update operator that appends a value to an array field "
          "atomically. It's equivalent to array.append() in Python, but it happens inside MongoDB in one atomic operation — "
          "no risk of two doctors writing to the same patient record simultaneously and overwriting each other.", BODY),
    ], RED_LT, RED))

    elems.append(sp())

    # ── SECTION 4: API KEYS ──────────────────────────────────────────────────
    elems += [hr(), p("4 — API Keys Required", H1)]

    elems.append(tworow_table([
        [p("GOOGLE_API_KEY", BODY_SMALL),
         p("Get from <b>aistudio.google.com/app/apikey</b>. Free. "
           "This lets Gemini read prescription images.", BODY_SMALL)],
        [p("MONGODB_URI", BODY_SMALL),
         p("Get from <b>MongoDB Atlas → Connect → Drivers</b>. "
           "Format: <font name='Courier'>mongodb+srv://user:pass@cluster.mongodb.net/cliniqai</font>. "
           "Free M0 cluster.", BODY_SMALL)],
    ]))

    elems.append(sp(4))
    elems.append(box([
        p("Without these keys the app still runs — it uses in-memory storage and "
          "returns a helpful error when you try to upload images. You can run all 7 tests "
          "without any API keys.", BODY_SMALL)
    ], AMBER_LT, AMBER))

    # ── SECTION 5: BUG REPORT ───────────────────────────────────────────────
    elems += [hr(), p("5 — Bug Discovery &amp; Auto-Fix Report", H1)]
    elems.append(p("Every bug found during Phase 1 build, with exact fix.", BODY))

    # Bug 1
    elems.append(KeepTogether([
        p("BUG #1 — Server crashes on startup  [CRITICAL]", H2),
        p("WHAT HAPPENED", LABEL_RED),
        box([p("When the .env file has placeholder values (youruser:yourpassword), PyMongo does a "
               "DNS lookup immediately at import time and throws "
               "<font name='Courier'>ConfigurationError: The DNS query name does not exist</font>. "
               "The server exits before any request is handled.", BODY)], RED_LT, RED),
        p("BEFORE", LABEL_RED),
        box([p("<font name='Courier' size='8.5'>client = MongoClient(MONGODB_URI)   # Line 32 — runs at import time<br/>"
               "db = client['cliniqai']             # Crashes here if URI is fake<br/>"
               "patients_collection = db['patients']</font>", BODY_SMALL)], CODE_BG, CODE_BG),
        p("AFTER", LABEL_EMERALD),
        box([p("<font name='Courier' size='8.5'>def get_db():<br/>"
               "    global client, db, patients_collection<br/>"
               "    if patients_collection is not None:<br/>"
               "        return True  # Already connected<br/>"
               "    if not MONGODB_URI or 'youruser' in MONGODB_URI:<br/>"
               "        return False  # Not configured — use in-memory<br/>"
               "    try:<br/>"
               "        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)<br/>"
               "        client.admin.command('ping')<br/>"
               "        ...</font>", BODY_SMALL)], CODE_BG, CODE_BG),
        p("ROOT CAUSE: Eager vs lazy initialization. The fix moves connection to first use.", BODY_SMALL),
    ]))

    elems.append(sp(8))

    # Bug 2
    elems.append(KeepTogether([
        p("BUG #2 — Non-image upload returns HTTP 500  [MEDIUM]", H2),
        p("WHAT HAPPENED", LABEL_RED),
        box([p("Uploading a .txt or corrupted file caused "
               "<font name='Courier'>PIL.UnidentifiedImageError</font> — unhandled exception → "
               "server returned a raw 500 error with no useful message to the frontend.", BODY)], RED_LT, RED),
        p("BEFORE", LABEL_RED),
        box([p("<font name='Courier' size='8.5'>image = Image.open(io.BytesIO(image_bytes))  # Crashes on non-images</font>", BODY_SMALL)], CODE_BG, CODE_BG),
        p("AFTER", LABEL_EMERALD),
        box([p("<font name='Courier' size='8.5'>try:<br/>"
               "    image = Image.open(io.BytesIO(image_bytes))<br/>"
               "except Exception as e:<br/>"
               "    return {'error': f'Could not read image file: {str(e)}. Please upload a valid JPG or PNG.'}</font>", BODY_SMALL)], CODE_BG, CODE_BG),
    ]))

    elems.append(sp(8))

    # Bug 3
    elems.append(KeepTogether([
        p("BUG #3 — No API key guard before calling Gemini  [MEDIUM]", H2),
        p("WHAT HAPPENED", LABEL_RED),
        box([p("With a placeholder key, "
               "<font name='Courier'>genai.configure(api_key='your_google_api_key_here')</font> "
               "doesn't fail immediately — it fails deep inside Google's library with a cryptic "
               "authentication error. Hard to debug.", BODY)], RED_LT, RED),
        p("AFTER", LABEL_EMERALD),
        box([p("<font name='Courier' size='8.5'>api_key = os.getenv('GOOGLE_API_KEY')<br/>"
               "if not api_key or 'your_google' in api_key:<br/>"
               "    return {'error': 'GOOGLE_API_KEY not configured. Set it in .env file.'}</font>", BODY_SMALL)], CODE_BG, CODE_BG),
    ]))

    elems.append(sp(8))

    # Bug 4
    elems.append(KeepTogether([
        p("BUG #4 — Regex injection in MongoDB query  [LOW]", H2),
        p("WHAT HAPPENED", LABEL_RED),
        box([p("A user query containing regex special characters like "
               "<font name='Courier'>test (patient)</font> would pass directly into "
               "<font name='Courier'>{'$regex': query}</font> — MongoDB would throw a regex parse error.", BODY)], RED_LT, RED),
        p("AFTER", LABEL_EMERALD),
        box([p("<font name='Courier' size='8.5'>import re<br/>"
               "safe_query = re.escape(query)  # Escapes (, ), [, ], ., * etc.<br/>"
               "patients = collection.find({'name': {'$regex': safe_query, '$options': 'i'}})</font>", BODY_SMALL)], CODE_BG, CODE_BG),
    ]))

    elems.append(sp(8))

    # Bug 5
    elems.append(KeepTogether([
        p("BUG #5 — Pinned dependency versions conflicted with google-adk  [LOW]", H2),
        p("WHAT HAPPENED", LABEL_RED),
        box([p("<font name='Courier'>fastapi==0.115.0</font> conflicted with "
               "<font name='Courier'>google-adk</font> which requires "
               "<font name='Courier'>fastapi>=0.124.1</font>. pip reported dependency conflicts.", BODY)], RED_LT, RED),
        p("AFTER", LABEL_EMERALD),
        box([p("<font name='Courier' size='8.5'># requirements.txt — use >= instead of ==<br/>"
               "fastapi>=0.124.1<br/>"
               "uvicorn>=0.34<br/>"
               "python-dotenv>=1.0.1</font>", BODY_SMALL)], CODE_BG, CODE_BG),
    ]))

    # ── SECTION 6: TEST RESULTS ──────────────────────────────────────────────
    elems += [hr(), p("6 — Test Results (All 7 Passed)", H1)]

    elems.append(tworow_table([
        [p("TEST 1", BODY_SMALL), p("Health check — server running, MongoDB status shown", BODY_SMALL)],
        [p("TEST 2", BODY_SMALL), p("Allergy alert: penicillin allergy + amoxicillin → HIGH alert fired", BODY_SMALL)],
        [p("TEST 3", BODY_SMALL), p("No alerts: safe medicines + no allergies → no alerts", BODY_SMALL)],
        [p("TEST 4", BODY_SMALL), p("Drug interaction: warfarin + aspirin → HIGH bleeding risk alert", BODY_SMALL)],
        [p("TEST 5", BODY_SMALL), p("Cross-allergy: penicillin allergy + cefixime → MEDIUM cross-allergy warning", BODY_SMALL)],
        [p("TEST 6", BODY_SMALL), p("Query endpoint: 'how many patients' → correct count returned", BODY_SMALL)],
        [p("TEST 7", BODY_SMALL), p("Recent patients: empty list returned correctly from in-memory store", BODY_SMALL)],
    ], col_widths=[2.5*cm, PAGE_W - MARGIN*2 - 2.5*cm - 0.4*cm]))

    # ── SECTION 7: WHY NOT THE ALTERNATIVES ─────────────────────────────────
    elems += [hr(), p("7 — Why Not the Alternatives", H1)]

    elems.append(tworow_table([
        [p("We used", BODY_SMALL), p("FastAPI", BODY_SMALL)],
        [p("Could have used", BODY_SMALL), p("Flask, Django", BODY_SMALL)],
        [p("Why FastAPI wins", BODY_SMALL),
         p("Async support + auto docs + Pydantic validation. Flask has none by default. Django is overkill.", BODY_SMALL)],
        [p("We used", BODY_SMALL), p("Rule-based alert_tool", BODY_SMALL)],
        [p("Could have used", BODY_SMALL), p("Ask Gemini to check interactions", BODY_SMALL)],
        [p("Why rules win", BODY_SMALL),
         p("Deterministic. A known allergy must trigger 100% of the time. LLMs are probabilistic — unsafe for life-critical checks.", BODY_SMALL)],
        [p("We used", BODY_SMALL), p("In-memory fallback store", BODY_SMALL)],
        [p("Could have used", BODY_SMALL), p("Crash with error if no MongoDB", BODY_SMALL)],
        [p("Why fallback wins", BODY_SMALL),
         p("Lets you develop and test the full flow locally without any cloud account. Faster dev loop.", BODY_SMALL)],
        [p("We used", BODY_SMALL), p("pymongo (direct)", BODY_SMALL)],
        [p("Could have used", BODY_SMALL), p("MongoDB MCP Server", BODY_SMALL)],
        [p("Why pymongo now", BODY_SMALL),
         p("Phase 1 is about getting core logic working cleanly. MCP adds complexity — it requires a running Node.js process. We add it in Phase 3 when the ADK agent needs it.", BODY_SMALL)],
    ], col_widths=[3.5*cm, PAGE_W - MARGIN*2 - 3.5*cm - 0.4*cm]))

    # ── SECTION 8: HOW TO RUN ────────────────────────────────────────────────
    elems += [hr(), p("8 — How to Run Phase 1", H1)]

    elems.append(box([
        p("<font name='Courier' size='9'># 1. Install dependencies</font>", BODY_SMALL),
        p("<font name='Courier' size='9'>cd cliniqai</font>", BODY_SMALL),
        p("<font name='Courier' size='9'>pip install -r requirements.txt</font>", BODY_SMALL),
        sp(4),
        p("<font name='Courier' size='9'># 2. Fill in your API keys</font>", BODY_SMALL),
        p("<font name='Courier' size='9'># Edit .env: set GOOGLE_API_KEY and MONGODB_URI</font>", BODY_SMALL),
        sp(4),
        p("<font name='Courier' size='9'># 3. Start the server</font>", BODY_SMALL),
        p("<font name='Courier' size='9'>python -m uvicorn agent.server:app --host 127.0.0.1 --port 8000 --reload</font>", BODY_SMALL),
        sp(4),
        p("<font name='Courier' size='9'># 4. Run all 7 tests (in a second terminal)</font>", BODY_SMALL),
        p("<font name='Courier' size='9'>python test_app.py</font>", BODY_SMALL),
        sp(4),
        p("<font name='Courier' size='9'># 5. Open interactive API docs</font>", BODY_SMALL),
        p("<font name='Courier' size='9'>http://127.0.0.1:8000/docs</font>", BODY_SMALL),
    ], CODE_BG, CODE_BG))

    # ── FOOTER ───────────────────────────────────────────────────────────────
    elems += [
        sp(20), hr(),
        p("CliniqAI Phase 1 Learning PDF · Google Cloud Rapid Agent Hackathon · MongoDB Track · May 2026",
          S("footer", fontSize=8, textColor=GRAY_TEXT, alignment=TA_CENTER, fontName="Helvetica")),
        p("Next: Phase 2 — Build the Web UI (HTML + Tailwind + Vanilla JS)",
          S("next", fontSize=9, textColor=EMERALD, alignment=TA_CENTER,
            fontName="Helvetica-Bold", spaceBefore=4)),
    ]

    doc.build(elems)
    print("PDF generated: CliniqAI_Phase_1_Learning.pdf")

if __name__ == "__main__":
    build()
