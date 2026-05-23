"""
Create a beautiful, professional PDF for Phase 1 Deep Explanation
Uses advanced styling, colors, boxes, and visual hierarchy
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, Image, HRFlowable
)
from reportlab.pdfgen import canvas
from reportlab.lib import colors as rcolors

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
    
    # Create table for box
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
    """Create a code block box"""
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
        "PHASE_1_DEEP_EXPLANATION_BEAUTIFUL.pdf",
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
        title="CliniqAI Phase 1 — Deep Explanation",
        author="CliniqAI Learning Guide",
    )

    elems = []

    # ── COVER ────────────────────────────────────────────────────────────────
    elems += [
        sp(50),
        p("CliniqAI Phase 1", TITLE),
        p("Deep Line-by-Line Explanation", SUBTITLE),
        sp(4),
        hr(EMERALD, 2),
        sp(20),
        p("Every variable explained", S("cov", fontSize=11, textColor=EMERALD, 
                                       alignment=TA_CENTER, fontName="Helvetica-Bold")),
        p("Every function broken down", S("cov", fontSize=11, textColor=BLUE, 
                                         alignment=TA_CENTER, fontName="Helvetica-Bold")),
        p("Every line with examples", S("cov", fontSize=11, textColor=RED, 
                                       alignment=TA_CENTER, fontName="Helvetica-Bold")),
        sp(60),
        p("Google Cloud Rapid Agent Hackathon · May 2026",
          S("cov", fontSize=9, textColor=GRAY_TEXT, alignment=TA_CENTER, fontName="Helvetica")),
    ]

    # ── TABLE OF CONTENTS ────────────────────────────────────────────────────
    elems += [
        PageBreak(),
        p("Table of Contents", H1),
        sp(4),
    ]

    toc_items = [
        ("Part 1", "Drug Conflict Checker (alert_tool.py)"),
        ("Part 2", "Vision Tool (vision_tool.py)"),
        ("Part 3", "Server Backend (server.py)"),
        ("Part 4", "Variable Tracing"),
    ]

    for num, title in toc_items:
        elems.append(p(f"<b>{num}:</b> {title}", BODY))

    # ── PART 1: ALERT TOOL ───────────────────────────────────────────────────
    elems += [
        PageBreak(),
        p("PART 1: Drug Conflict Checker", H1),
        p("Understanding alert_tool.py", BODY_SMALL),
        sp(6),
        hr(EMERALD),
    ]

    # Concept 1: Allergy Families
    elems += concept_section(
        "Concept 1: What is an Allergy Family?",
        "Imagine you're allergic to peanuts. Peanuts are in the 'legume' family. Other legumes include lentils, chickpeas, soybeans. If you're allergic to peanuts, you might also be allergic to other legumes. Doctors group them together. In CliniqAI, we do the same with medicines.",
        [
            p("<b>Allergy families are dictionaries that group similar drugs:</b>", BODY),
            code_box('''ALLERGY_FAMILIES = {
    "penicillin": ["amoxicillin", "ampicillin", "augmentin", ...],
    "cephalosporin": ["cefalexin", "cefuroxime", "cefixime", ...],
}'''),
            p("<b>Key:</b> Family name (e.g., 'penicillin')<br/><b>Value:</b> List of drugs in that family", BODY_SMALL),
        ],
        [
            p("<b>Example:</b>", BODY_SMALL),
            code_box('''Patient's allergy: "penicillin"
New prescription: "Amoxicillin"

Check: Is "amoxicillin" in ALLERGY_FAMILIES["penicillin"]?
Answer: YES → ALERT!'''),
        ]
    )
    elems += elems[-3:]  # Add the concept section
    elems = elems[:-3]

    # Direct Allergy Check
    elems += [
        p("Layer 1: Direct Allergy Check", H2),
        sp(4),
    ]

    elems += concept_section(
        "How Direct Allergy Checking Works",
        "A pharmacist checks: 'Is the patient allergic to this exact drug family?' They look at the patient's known allergies and the new prescription, and see if there's a match.",
        [
            p("<b>The code loops through 3 things:</b>", BODY),
            p("1. Each patient allergy", BULLET),
            p("2. Each drug family in the database", BULLET),
            p("3. Each new medicine in the prescription", BULLET),
            sp(4),
            code_box('''for allergy in patient_allergies:
    allergy_lower = allergy.lower()
    for family, drugs in ALLERGY_FAMILIES.items():
        if allergy_lower == family or allergy_lower in drugs:
            for new_name in new_med_names:
                if any(drug in new_name for drug in drugs):
                    alerts.append({"severity": "HIGH", ...})'''),
        ],
        [
            p("<b>Example:</b>", BODY_SMALL),
            code_box('''Patient allergies: ["penicillin"]
New medicines: ["amoxicillin", "paracetamol"]

Loop 1: allergy = "penicillin"
Loop 2: family = "penicillin", drugs = ["amoxicillin", ...]
Loop 3: new_name = "amoxicillin"

Check: Is "amoxicillin" in ["amoxicillin", ...]?
YES → Add HIGH alert!'''),
        ]
    )
    elems += elems[-3:]
    elems = elems[:-3]

    # ── PART 2: VISION TOOL ──────────────────────────────────────────────────
    elems += [
        PageBreak(),
        p("PART 2: Vision Tool", H1),
        p("Understanding vision_tool.py", BODY_SMALL),
        sp(6),
        hr(BLUE),
    ]

    elems += concept_section(
        "Image Processing: Image.open(io.BytesIO(image_bytes))",
        "Imagine you receive a photo as a stream of binary data (1s and 0s). You need to convert it into something you can actually look at — an image object. That's what this line does.",
        [
            p("<b>Breaking it down:</b>", BODY),
            p("<font color='#2563eb'><b>io.BytesIO(image_bytes)</b></font> — Convert raw bytes into a file-like object", BULLET),
            p("<font color='#2563eb'><b>Image.open(...)</b></font> — Open and validate the image", BULLET),
            p("<font color='#2563eb'><b>try...except</b></font> — Catch errors if it's not a valid image", BULLET),
            sp(4),
            code_box('''try:
    image = Image.open(io.BytesIO(image_bytes))
except Exception as e:
    return {"error": f"Could not read image file: {str(e)}"}'''),
        ],
        [
            p("<b>Example:</b>", BODY_SMALL),
            code_box('''User uploads: document.txt (NOT an image!)

Image.open() throws: UnidentifiedImageError

We catch it and return:
{"error": "Could not read image file: cannot identify image file. 
Please upload a valid JPG or PNG."}'''),
        ]
    )
    elems += elems[-3:]
    elems = elems[:-3]

    # ── PART 3: SERVER.PY ────────────────────────────────────────────────────
    elems += [
        PageBreak(),
        p("PART 3: Server Backend", H1),
        p("Understanding server.py", BODY_SMALL),
        sp(6),
        hr(RED),
    ]

    elems += concept_section(
        "Loading Environment Variables",
        "Your API keys (like GOOGLE_API_KEY) are secrets. You don't want to hardcode them in your code. Instead, you put them in a .env file and load them at runtime.",
        [
            p("<b>The process:</b>", BODY),
            p("1. Create a .env file with your secrets", BULLET),
            p("2. Call load_dotenv() to read the file", BULLET),
            p("3. Use os.getenv() to access the values", BULLET),
            sp(4),
            code_box('''# .env file
GOOGLE_API_KEY=sk-proj-abc123...
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/cliniqai

# In Python
load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")'''),
        ],
        [
            p("<b>Example:</b>", BODY_SMALL),
            code_box('''After load_dotenv():

MONGODB_URI = "mongodb+srv://user:pass@cluster.mongodb.net/cliniqai"
GOOGLE_API_KEY = "sk-proj-abc123..."

These are now available throughout your code!'''),
        ]
    )
    elems += elems[-3:]
    elems = elems[:-3]

    # ── PART 4: VARIABLE TRACING ─────────────────────────────────────────────
    elems += [
        PageBreak(),
        p("PART 4: Variable Tracing", H1),
        p("Where every variable comes from", BODY_SMALL),
        sp(6),
        hr(AMBER),
    ]

    trace_data = [
        ["Variable", "Where it comes from", "Example"],
        ["image_bytes", "User uploads file → file.read()", "b'\\x89PNG...'"],
        ["extracted", "Gemini Vision → extract_from_prescription()", "{'patient_name': 'Ramesh', ...}"],
        ["patient_name", "extracted.get('patient_name')", "'Ramesh Gupta'"],
        ["existing_patient", "MongoDB search → find_one()", "{_id, name, visits, ...}"],
        ["visit", "Built from extracted data", "{date, doctor, medicines, ...}"],
        ["patient_allergies", "Combined list → list(set(...))", "['penicillin', 'sulfa']"],
        ["new_medicines", "extracted.get('medicines')", "[{name, dose, ...}]"],
        ["conflict_result", "Alert tool → check_drug_conflicts()", "{has_alerts, alerts, ...}"],
    ]

    trace_table = Table(trace_data, colWidths=[3*cm, 4.5*cm, 4.5*cm])
    trace_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AMBER),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, GRAY_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, GRAY_BG]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    elems.append(trace_table)

    # ── FOOTER ───────────────────────────────────────────────────────────────
    elems += [
        sp(30),
        hr(GRAY_BORDER),
        p("CliniqAI Phase 1 Deep Explanation · Beautiful PDF Edition",
          S("footer", fontSize=9, textColor=GRAY_TEXT, alignment=TA_CENTER, fontName="Helvetica")),
        p("Ready to move to Phase 2: Web UI",
          S("next", fontSize=10, textColor=EMERALD, alignment=TA_CENTER,
            fontName="Helvetica-Bold", spaceBefore=4)),
    ]

    doc.build(elems)
    print("✓ Beautiful PDF created: PHASE_1_DEEP_EXPLANATION_BEAUTIFUL.pdf")

if __name__ == "__main__":
    build()
