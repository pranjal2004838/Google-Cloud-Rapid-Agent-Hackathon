import os
import sys
import uuid
import json
import urllib.request
from datetime import date, datetime
from PIL import Image, ImageDraw, ImageFont

# Ensure the cliniqai package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from agent import server
from agent.orchestration.state import WorkflowStatus

# Connect to live MongoDB and clear collection for fresh test run
if server.get_db():
    server.patients_collection.delete_many({})
    print("Cleared live MongoDB 'patients' collection for a clean test run.")
else:
    print("MongoDB not configured or failed to connect, running in-memory fallback mode.")
    server.in_memory_patients.clear()

client = TestClient(server.app)

# ─── Font Setup ──────────────────────────────────────────────────────────────
def get_handwriting_font():
    """Download a cursive font from Google Fonts or fall back to Windows Segoe Print."""
    font_filename = "MrsSaintDelafield-Regular.ttf"
    if not os.path.exists(font_filename):
        print("Downloading MrsSaintDelafield font from Google Fonts for handwriting simulation...")
        try:
            url = "https://github.com/google/fonts/raw/main/ofl/mrssaintdelafield/MrsSaintDelafield-Regular.ttf"
            urllib.request.urlretrieve(url, font_filename)
            print("Download completed successfully!")
        except Exception as e:
            print(f"Could not download MrsSaintDelafield font ({e}). Trying Windows Segoe Print...")
            
    # System font fallback chain
    win_cursive = "C:/Windows/Fonts/segoepr.ttf"  # Segoe Print
    win_comic = "C:/Windows/Fonts/comic.ttf"      # Comic Sans
    
    candidates = [font_filename, "MrsSaintDelafield.ttf", win_cursive, win_comic]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

FONT_PATH = get_handwriting_font()

# ─── Prescription Image Generator ────────────────────────────────────────────
def generate_prescription_image(metadata: dict, output_path: str, language: str = "en"):
    """
    Generate an off-white simulated paper prescription with clean printed labels
    and messy, scribbled doctor-style handwriting.
    """
    width, height = 750, 950
    # Cream/off-white color
    bg_color = (252, 250, 242)
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Dictionary of localized headers
    headers = {
        "en": {
            "title": "CITY GENERAL CLINIC",
            "reg": "Reg. ID: IN-57701-A",
            "patient": "Patient Name:",
            "phone": "Phone:",
            "age_gender": "Age / Gender:",
            "date": "Date:",
            "diag": "Diagnosis:",
            "rx": "Rx",
            "meds": "Prescribed Medicines:",
            "allergies": "Known Allergies:",
            "notes": "Notes:",
            "sig": "Doctor Signature"
        },
        "es": {
            "title": "CLINICA GENERAL SAN JOSE",
            "reg": "Registro N: ES-34401-B",
            "patient": "Nombre Paciente:",
            "phone": "Telefono:",
            "age_gender": "Edad / Genero:",
            "date": "Fecha:",
            "diag": "Diagnostico:",
            "rx": "Rp",
            "meds": "Medicinas Recetadas:",
            "allergies": "Alergias Conocidas:",
            "notes": "Notas:",
            "sig": "Firma del Medico"
        },
        "fr": {
            "title": "CABINET MEDICAL DE PARIS",
            "reg": "Licence N: FR-88402-C",
            "patient": "Nom du Patient:",
            "phone": "Telephone:",
            "age_gender": "Age / Sexe:",
            "date": "Date:",
            "diag": "Diagnostic:",
            "rx": "Ordonnance",
            "meds": "Medicaments Prescrits:",
            "allergies": "Allergies Connues:",
            "notes": "Notes:",
            "sig": "Signature du Medecin"
        },
        "it": {
            "title": "STUDIO MEDICO ROSSI",
            "reg": "Iscrizione N: IT-99201-D",
            "patient": "Nome Paziente:",
            "phone": "Telefono:",
            "age_gender": "Eta / Sesso:",
            "date": "Data:",
            "diag": "Diagnosi:",
            "rx": "Ricetta",
            "meds": "Farmaci Prescritti:",
            "allergies": "Allergie Note:",
            "notes": "Note:",
            "sig": "Firma del Medico"
        },
        "hi": {
            "title": "CITY GENERAL CLINIC (HINDI)",
            "reg": "REG NO: IN-7789-H",
            "patient": "Patient Name:",
            "phone": "Phone:",
            "age_gender": "Age / Gender:",
            "date": "Date:",
            "diag": "Diagnosis:",
            "rx": "Rx",
            "meds": "Medicines:",
            "allergies": "Allergies:",
            "notes": "Notes:",
            "sig": "Doctor Signature"
        }
    }

    lang_headers = headers.get(language, headers["en"])

    # Load clean fonts for layout
    try:
        font_print_title = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 26)
        font_print_label = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 15)
        font_print_sub = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 13)
        font_print_rx = ImageFont.truetype("C:/Windows/Fonts/timesbd.ttf", 44)
    except Exception:
        font_print_title = font_print_label = font_print_sub = font_print_rx = ImageFont.load_default()

    # Load messy doctor handwriting font
    try:
        if FONT_PATH:
            font_hw_name = ImageFont.truetype(FONT_PATH, 34)
            font_hw_body = ImageFont.truetype(FONT_PATH, 30)
            font_hw_sig = ImageFont.truetype(FONT_PATH, 42)
        else:
            font_hw_name = font_hw_body = font_hw_sig = ImageFont.load_default()
    except Exception:
        font_hw_name = font_hw_body = font_hw_sig = ImageFont.load_default()

    # Draw header (clean printed style)
    draw.text((60, 55), lang_headers["title"], fill=(30, 40, 80), font=font_print_title)
    draw.text((60, 95), lang_headers["reg"], fill=(100, 100, 110), font=font_print_sub)
    draw.line([(60, 130), (width - 60, 130)], fill=(180, 180, 200), width=2)

    # Patient info form layout (printed labels, doctor scribbles)
    # Patient Name
    draw.text((60, 150), lang_headers["patient"], fill=(80, 80, 80), font=font_print_label)
    draw.text((180, 138), metadata["patient_name"], fill=(15, 20, 110), font=font_hw_name)
    
    # Phone
    draw.text((60, 185), lang_headers["phone"], fill=(80, 80, 80), font=font_print_label)
    draw.text((180, 173), metadata["phone"], fill=(15, 20, 110), font=font_hw_body)
    
    # Age/Gender
    draw.text((60, 220), lang_headers["age_gender"], fill=(80, 80, 80), font=font_print_label)
    draw.text((180, 208), f"{metadata.get('patient_age')} / {metadata.get('patient_gender')}", fill=(15, 20, 110), font=font_hw_body)
    
    # Date
    draw.text((width - 250, 150), lang_headers["date"], fill=(80, 80, 80), font=font_print_label)
    draw.text((width - 190, 138), metadata["visit_date"], fill=(15, 20, 110), font=font_hw_body)
    
    draw.line([(60, 260), (width - 60, 260)], fill=(210, 210, 220), width=1)

    # Rx Symbol
    draw.text((60, 280), lang_headers["rx"], fill=(150, 20, 20), font=font_print_rx)

    # Doctor name in print
    draw.text((width - 250, 285), f"Dr. {metadata.get('doctor_name', 'AI Doctor')}", fill=(60, 60, 90), font=font_print_label)

    y = 350
    # Diagnosis
    if metadata.get("diagnosis"):
        draw.text((60, y), lang_headers["diag"], fill=(80, 80, 80), font=font_print_label)
        diag_text = ", ".join(metadata["diagnosis"])
        draw.text((160, y - 10), diag_text, fill=(15, 20, 110), font=font_hw_body)
        y += 50

    # Medicines List
    draw.text((60, y), lang_headers["meds"], fill=(80, 80, 80), font=font_print_label)
    y += 30
    for med in metadata.get("medicines", []):
        med_str = f" - {med['name']} {med['dose']} ({med['frequency']}, {med['duration']})"
        draw.text((80, y - 8), med_str, fill=(15, 20, 110), font=font_hw_body)
        y += 45

    # Allergies
    if metadata.get("allergies_mentioned"):
        draw.text((60, y), lang_headers["allergies"], fill=(180, 30, 30), font=font_print_label)
        alg_text = ", ".join(metadata["allergies_mentioned"])
        draw.text((190, y - 10), alg_text, fill=(180, 30, 30), font=font_hw_body)
        y += 50

    # Notes
    if metadata.get("notes"):
        draw.text((60, y), lang_headers["notes"], fill=(80, 80, 80), font=font_print_label)
        draw.text((120, y - 10), metadata["notes"], fill=(50, 50, 70), font=font_hw_body)

    # Doctor signature line
    draw.line([(width - 250, height - 100), (width - 60, height - 100)], fill=(120, 120, 120), width=1)
    draw.text((width - 210, height - 145), metadata.get("doctor_name", "AI Doctor"), fill=(15, 20, 110), font=font_hw_sig)
    draw.text((width - 200, height - 90), lang_headers["sig"], fill=(100, 100, 100), font=font_print_sub)

    # Apply small rotation to make it feel scanned/hand-held
    img = img.rotate(1.2, fillcolor=bg_color)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "JPEG")


# ─── Define 10 Prescription Lifecycle Datasets ──────────────────────────────
prescriptions_dataset = [
    # ─── Patient 1: Rajesh Kumar (English, 3 visits) ───
    {
        "id": 1,
        "language": "en",
        "phone": "9988776611",
        "patient_name": "Rajesh Kumar",
        "patient_age": 45,
        "patient_gender": "Male",
        "visit_date": "2026-05-10",
        "doctor_name": "Amit Sharma",
        "clinic_name": "City General Clinic",
        "diagnosis": ["Acute Bronchitis"],
        "medicines": [
            {"name": "Amoxicillin", "dose": "500mg", "frequency": "thrice daily", "duration": "5 days"},
            {"name": "Paracetamol", "dose": "650mg", "frequency": "as needed", "duration": "3 days"}
        ],
        "allergies_mentioned": [],
        "notes": "Rest for 3 days and drink plenty of fluids."
    },
    {
        "id": 2,
        "language": "en",
        "phone": "9988776611",
        "patient_name": "Rajesh Kumar",
        "patient_age": 45,
        "patient_gender": "Male",
        "visit_date": "2026-05-20",
        "doctor_name": "Amit Sharma",
        "clinic_name": "City General Clinic",
        "diagnosis": ["Essential Hypertension"],
        "medicines": [
            {"name": "Metformin", "dose": "500mg", "frequency": "twice daily", "duration": "30 days"},
            {"name": "Amlodipine", "dose": "5mg", "frequency": "once daily", "duration": "30 days"}
        ],
        "allergies_mentioned": [],
        "notes": "Monitor blood pressure daily."
    },
    {
        "id": 3,
        "language": "en",
        "phone": "9988776611",
        "patient_name": "Rajesh Kumar",
        "patient_age": 45,
        "patient_gender": "Male",
        "visit_date": "2026-06-01",
        "doctor_name": "Amit Sharma",
        "clinic_name": "City General Clinic",
        "diagnosis": ["Chronic Back Pain"],
        "medicines": [
            {"name": "Ibuprofen", "dose": "400mg", "frequency": "twice daily", "duration": "10 days"}
        ],
        "allergies_mentioned": [],
        "notes": "Take after meals to avoid acidity."
    },

    # ─── Patient 2: Maria Rodriguez (Spanish, 2 visits) ───
    {
        "id": 4,
        "language": "es",
        "phone": "9988776622",
        "patient_name": "Maria Rodriguez",
        "patient_age": 38,
        "patient_gender": "Female",
        "visit_date": "2026-05-15",
        "doctor_name": "Carlos Ruiz",
        "clinic_name": "Clinica Medica San Jose",
        "diagnosis": ["Infeccion de Garganta"],
        "medicines": [
            {"name": "Amoxicillin", "dose": "500mg", "frequency": "thrice daily", "duration": "7 days"},
            {"name": "Paracetamol", "dose": "500mg", "frequency": "three times daily", "duration": "4 days"}
        ],
        "allergies_mentioned": [],
        "notes": "Tomar mucha agua tibia."
    },
    {
        "id": 5,
        "language": "es",
        "phone": "9988776622",
        "patient_name": "Maria Rodriguez",
        "patient_age": 38,
        "patient_gender": "Female",
        "visit_date": "2026-05-30",
        "doctor_name": "Carlos Ruiz",
        "clinic_name": "Clinica Medica San Jose",
        "diagnosis": ["Fiebre y Fatiga"],
        "medicines": [
            {"name": "Metformin", "dose": "850mg", "frequency": "twice daily", "duration": "continuous"}
        ],
        "allergies_mentioned": [],
        "notes": "Control de azucar en sangre."
    },

    # ─── Patient 3: Priya Sharma (Hindi/Transliterated, 2 visits - Allergy case) ───
    {
        "id": 6,
        "language": "hi",
        "phone": "9988776633",
        "patient_name": "Priya Sharma",
        "patient_age": 29,
        "patient_gender": "Female",
        "visit_date": "2026-05-12",
        "doctor_name": "Sneha Patel",
        "clinic_name": "Lotus Medical Center",
        "diagnosis": ["Allergic Rhinitis"],
        "medicines": [
            {"name": "Cetirizine", "dose": "10mg", "frequency": "once daily at night", "duration": "10 days"}
        ],
        "allergies_mentioned": ["penicillin"],
        "notes": "Avoid cold foods. Allergies mentioned: penicillin."
    },
    {
        "id": 7,
        "language": "hi",
        "phone": "9988776633",
        "patient_name": "Priya Sharma",
        "patient_age": 29,
        "patient_gender": "Female",
        "visit_date": "2026-05-22",
        "doctor_name": "Sneha Patel",
        "clinic_name": "Lotus Medical Center",
        "diagnosis": ["Otitis Media"],
        "medicines": [
            {"name": "Amoxicillin", "dose": "500mg", "frequency": "thrice daily", "duration": "7 days"}
        ],
        "allergies_mentioned": ["penicillin"],
        "notes": "Triggers Penicillin Allergy conflict warning!"
    },

    # ─── Patient 4: Jean Dupont (French, 1 visit) ───
    {
        "id": 8,
        "language": "fr",
        "phone": "9988776644",
        "patient_name": "Jean Dupont",
        "patient_age": 55,
        "patient_gender": "Male",
        "visit_date": "2026-05-25",
        "doctor_name": "Jean-Pierre Blanc",
        "clinic_name": "Cabinet Medical",
        "diagnosis": ["Migraine Aigue"],
        "medicines": [
            {"name": "Aspirin", "dose": "500mg", "frequency": "as needed", "duration": "5 days"}
        ],
        "allergies_mentioned": [],
        "notes": "Se reposer dans une chambre sombre."
    },

    # ─── Patient 5: Giovanni Rossi (Italian, 2 visits - Dangerous Combo Case) ───
    {
        "id": 9,
        "language": "it",
        "phone": "9988776655",
        "patient_name": "Giovanni Rossi",
        "patient_age": 62,
        "patient_gender": "Male",
        "visit_date": "2026-05-18",
        "doctor_name": "Marco Bianchi",
        "clinic_name": "Studio Medico Rossi",
        "diagnosis": ["Fibrillazione Atriale"],
        "medicines": [
            {"name": "Warfarin", "dose": "5mg", "frequency": "once daily", "duration": "continuous"}
        ],
        "allergies_mentioned": [],
        "notes": "Monitorare INR settimanalmente."
    },
    {
        "id": 10,
        "language": "it",
        "phone": "9988776655",
        "patient_name": "Giovanni Rossi",
        "patient_age": 62,
        "patient_gender": "Male",
        "visit_date": "2026-06-03",
        "doctor_name": "Marco Bianchi",
        "clinic_name": "Studio Medico Rossi",
        "diagnosis": ["Artrite e dolore articolare"],
        "medicines": [
            {"name": "Aspirin", "dose": "100mg", "frequency": "once daily", "duration": "10 days"}
        ],
        "allergies_mentioned": [],
        "notes": "Triggers Warfarin + Aspirin HIGH severity interaction check!"
    }
]


# ─── Running the test pipeline ────────────────────────────────────────────────
def run_upload_test(metadata: dict, filepath: str):
    """
    Attempts to process the prescription via live GCP endpoint `/process`.
    If GCP Vertex AI permissions fail, falls back to `/test/process`
    which bypasses Vertex AI but runs the remainder of the multi-agent system.
    """
    # Emojis replaced with ASCII safe strings
    print(f"\n[PROCESS] [Prescription #{metadata['id']}] Processing: Patient '{metadata['patient_name']}' ({metadata['language'].upper()}) - Date: {metadata['visit_date']}")
    
    # Check if file exists, if not generate it
    if not os.path.exists(filepath):
        generate_prescription_image(metadata, filepath, metadata["language"])
        print(f"  -> Generated prescription image: {filepath}")

    # Step 1: Attempt Live API Process
    use_override = True
    response_data = None
    
    # Try calling the live endpoint
    try:
        with open(filepath, "rb") as f:
            files = {"file": (os.path.basename(filepath), f, "image/jpeg")}
            form_data = {"phone": metadata["phone"]}
            
            # Make the API call to FastAPI server via TestClient
            print("  -> Posting prescription to live /process endpoint...")
            response = client.post("/process", data=form_data, files=files)
            
            if response.status_code == 200:
                resp_json = response.json()
                if "error" not in resp_json:
                    print("  [OK] Live Vertex AI extraction succeeded!")
                    response_data = resp_json
                    use_override = False
                else:
                    print(f"  [WARN] Live API reported internal error: {resp_json['error']}")
            else:
                print(f"  [WARN] Live API endpoint returned HTTP status {response.status_code}")
    except Exception as e:
        print(f"  [WARN] Live API connection failed: {e}")

    # Step 2: Fall back to override mode (runs Supervisor & other Agents)
    if use_override:
        print("  [WARN] GCP credentials/billing missing or failed. Using Override Endpoint /test/process...")
        
        # Structure payload to match ExtractionAgent schema
        # Simulate confidence scores
        confidence = {
            "patient_name": 0.95,
            "patient_age": 0.90,
            "patient_gender": 0.95,
            "visit_date": 0.90,
            "doctor_name": 0.90,
            "clinic_name": 0.85,
            "diagnosis": 0.90,
            "medicines": [{"name": 0.92, "dose": 0.90, "frequency": 0.90, "duration": 0.90} for _ in metadata["medicines"]],
            "tests_ordered": 0.90,
            "allergies_mentioned": 0.95,
            "notes": 0.85
        }
        
        override_payload = {
            "phone": metadata["phone"],
            "patient_name": metadata["patient_name"],
            "patient_age": metadata["patient_age"],
            "patient_gender": metadata["patient_gender"],
            "visit_date": metadata["visit_date"],
            "doctor_name": metadata["doctor_name"],
            "clinic_name": metadata["clinic_name"],
            "diagnosis": metadata["diagnosis"],
            "medicines": metadata["medicines"],
            "tests_ordered": [],
            "allergies_mentioned": metadata["allergies_mentioned"],
            "notes": metadata["notes"],
            "confidence": confidence,
            "source_document": {
                "bucket": "cliniqai-test-bucket",
                "object": os.path.basename(filepath),
                "uri": f"gs://cliniqai-test-bucket/{os.path.basename(filepath)}",
                "content_type": "image/jpeg"
            }
        }
        
        response = client.post("/test/process", json=override_payload)
        if response.status_code == 200:
            response_data = response.json()
            print("  [OK] Override test processing completed successfully!")
        else:
            print(f"  [FAIL] Override test failed with HTTP status {response.status_code}")
            return None

    return response_data


# ─── Main Execution and Testing Verification ─────────────────────────────────
def main():
    print("======================================================================")
    print("          CLINIQAI INTENSIVE TESTING RUNNER (10 PRESCRIPTIONS)")
    print("======================================================================\n")

    os.makedirs("generated_prescriptions", exist_ok=True)
    
    results = []
    
    # Process all 10 prescriptions in order
    for rx in prescriptions_dataset:
        filename = f"generated_prescriptions/rx_{rx['id']}_{rx['patient_name'].lower().replace(' ', '_')}_{rx['visit_date']}.jpg"
        
        # Run upload & processing
        res = run_upload_test(rx, filename)
        if res:
            results.append({
                "meta": rx,
                "output": res
            })
        else:
            print(f"  [FAIL] Severe Failure: Could not get response for Rx #{rx['id']}")
            sys.exit(1)

    print("\n======================================================================")
    print("                       VERIFICATION & AUDITING                        ")
    print("======================================================================\n")
    
    all_passed = True

    # 1. Verify Patient visit lifecycle & record integrity
    print("[TEST 1] Patient Visit Append / Count Verification:")
    p1_results = [r for r in results if r["meta"]["phone"] == "9988776611"]
    p2_results = [r for r in results if r["meta"]["phone"] == "9988776622"]
    
    print(f"  * Rajesh Kumar (Patient 1) uploads: {len(p1_results)} / 3 visits expected.")
    # Check what visit count the DB thinks
    p1_db_visit_count = p1_results[-1]["output"]["patient"]["visit_count"]
    print(f"  * Rajesh Kumar DB visit_count field: {p1_db_visit_count} (Expected: 3)")
    if p1_db_visit_count != 3:
        print("    [FAIL] Visit count mismatch!")
        all_passed = False
    else:
        print("    [PASS]")

    print(f"  * Maria Rodriguez (Patient 2) uploads: {len(p2_results)} / 2 visits expected.")
    p2_db_visit_count = p2_results[-1]["output"]["patient"]["visit_count"]
    print(f"  * Maria Rodriguez DB visit_count field: {p2_db_visit_count} (Expected: 2)")
    if p2_db_visit_count != 2:
        print("    [FAIL] Visit count mismatch!")
        all_passed = False
    else:
        print("    [PASS]")

    # 2. Verify PII KMS encryption
    print("\n[TEST 2] Patient KMS Encryption Verification:")
    # We inspect the raw server database to check how data is saved (live DB or in-memory)
    if server.get_db():
        patient_in_db = server.patients_collection.find_one({"phone": "9988776611"})
    else:
        patient_in_db = next((p for p in server.in_memory_patients if p["phone"] == "9988776611"), None)
    
    if patient_in_db:
        print(f"  * Raw DB Name field: {patient_in_db['name']}")
        print(f"  * Raw DB Age field: {patient_in_db['age']}")
        print(f"  * Raw DB secure_pii field exists: {bool(patient_in_db.get('secure_pii'))}")
        
        # Verify encryption placeholder
        if patient_in_db["name"] == "[ENCRYPTED_KMS]" and "secure_pii" in patient_in_db:
            print("    [PASS] (PII is encrypted using KMS/Base64 wrapper)")
        else:
            print("    [FAIL] (PII was stored as plain text)")
            all_passed = False
            
        # Verify Decryption on GET `/patient/{phone}`
        print("  * Fetching patient via GET /patient/9988776611...")
        get_res = client.get("/patient/9988776611")
        get_data = get_res.json()
        if get_data["found"] and get_data["patient"]["name"] == "Rajesh Kumar":
            print(f"    [PASS] (PII decrypted on-the-fly. Returned name: {get_data['patient']['name']})")
        else:
            print(f"    [FAIL] (Decryption returned wrong name: {get_data.get('patient', {}).get('name')})")
            all_passed = False
    else:
        print("  [FAIL] Patient not found in DB store!")
        all_passed = False

    # 3. Verify Allergy conflict alerts
    print("\n[TEST 3] Penicillin Allergy Alert Detection:")
    # Priya Sharma's second prescription is Amoxicillin (Penicillin family)
    priya_res = results[6] # Rx #7
    alerts = priya_res["output"]["alerts"]
    print("  * Alerts generated for Priya Sharma Ear Infection visit:")
    for a in alerts:
        print(f"    -> [{a['severity']}] Type: {a['type']} - Message: {a['message']}")
    
    allergy_triggered = any(a["type"] == "ALLERGY" and "penicillin" in a["message"].lower() for a in alerts)
    if allergy_triggered and priya_res["output"]["workflow_status"] == WorkflowStatus.REVIEW_REQUIRED.value:
        print("    [PASS] (Penicillin allergy alert correctly triggered and workflow routed to REVIEW_REQUIRED)")
    else:
        print("    [FAIL] (No allergy alert triggered or status not set to REVIEW_REQUIRED)")
        all_passed = False

    # 4. Verify Dangerous Drug combination alert (Warfarin + Aspirin)
    print("\n[TEST 4] Warfarin + Aspirin Dangerous Combination Detection:")
    giovanni_res = results[9] # Rx #10
    g_alerts = giovanni_res["output"]["alerts"]
    print("  * Alerts generated for Giovanni Rossi (Aspirin when on Warfarin):")
    for a in g_alerts:
        print(f"    -> [{a['severity']}] Type: {a['type']} - Message: {a['message']}")
        
    combo_triggered = any(
        a["type"] == "INTERACTION" 
        and a["severity"] == "HIGH" 
        and ("bleeding" in a["message"].lower() or "hemorrhagic" in a["message"].lower())
        for a in g_alerts
    )
    if combo_triggered and giovanni_res["output"]["workflow_status"] == WorkflowStatus.REVIEW_REQUIRED.value:
        print("    [PASS] (Warfarin + Aspirin interaction check was triggered successfully)")
    else:
        print("    [FAIL] (Dangerous drug combination not detected!)")
        all_passed = False

    # 5. Verify Duplicate visit check
    print("\n[TEST 5] Duplicate Visit Prevention Verification:")
    # Upload same prescription for Patient 1 within seconds
    print("  * Uploading Rajesh Kumar's Rx #3 a second time...")
    filename_dup = "generated_prescriptions/rx_3_rajesh_kumar_2026-06-01.jpg"
    res_dup = run_upload_test(prescriptions_dataset[2], filename_dup)
    
    if res_dup and res_dup["duplicate_check"]["is_duplicate"]:
        print(f"    [PASS] (Duplicate detected. Similarity: {res_dup['duplicate_check']['similarity']}, warning: {res_dup['duplicate_check']['warning']})")
    else:
        print("    [FAIL] (Duplicate was not detected or warning missing)")
        all_passed = False

    # 6. Verify Chatbot persistent history Integration
    print("\n[TEST 6] Multi-Agent Chatbot Integration & History Scoping:")
    # Ask chatbot questions
    # Chat 1: Ask about Rajesh's medicines
    chat1 = client.post("/chat", json={
        "phone": "9988776611",
        "doctor_id": "dr_amit_sharma",
        "query": "Which medicines was Rajesh Kumar prescribed in his visits?"
    })
    print(f"  * Chat Question 1: 'Which medicines was Rajesh Kumar prescribed?'")
    print(f"    Chat Answer: {chat1.json()['answer']}")
    
    # Chat 2: Ask about Priya's allergies
    chat2 = client.post("/chat", json={
        "phone": "9988776633",
        "doctor_id": "dr_sneha_patel",
        "query": "Does Priya have any drug allergies that I should know about?"
    })
    print(f"  * Chat Question 2: 'Does Priya have any drug allergies?'")
    print(f"    Chat Answer: {chat2.json()['answer']}")
    
    if "penicillin" in chat2.json()["answer"].lower():
        print("    [PASS] (Chatbot successfully extracted allergies from patient context)")
    else:
        print("    [FAIL] (Chatbot answers missing critical allergy information)")
        all_passed = False

    # 7. Verify alert acknowledgment & immutable audit logging
    print("\n[TEST 7] Alert Acknowledgment & Immutable Audit Trail Integrity:")
    # Acknowledge Giovanni's alert
    ack_res = client.post("/alerts/acknowledge", json={
        "phone": "9988776655",
        "doctor_name": "Marco Bianchi",
        "alert": "WARFARIN + ASPIRIN",
        "override_reason": "Patient is on low dose aspirin under strict cardiologist supervision"
    })
    
    ack_data = ack_res.json()
    print(f"  * Acknowledgment output event action: {ack_data['event']['action']}")
    print(f"  * Acknowledgment reason saved: {ack_data['event']['details']['override_reason']}")
    print(f"  * Audit chain validity: {ack_data['chain_valid']}")
    print(f"  * Total audit entries in DB: {ack_data['audit_entries']}")
    
    if ack_data["ok"] and ack_data["chain_valid"] and ack_data["audit_entries"] == 3:
        print("    [PASS] (Acknowledgment appended to audit log, hash chain intact)")
    else:
        print("    [FAIL] (Alert acknowledgment failed or broke hash chain integrity)")
        all_passed = False

    # Summarize all tests
    print("\n" + "=" * 70)
    if all_passed:
        print(" [SUCCESS] ALL INTENSIVE SYSTEM TESTS PASSED SUCCESSFULLY! ")
    else:
        print(" [FAIL] SOME INTENSIVE SYSTEM TESTS FAILED!")
    print("=" * 70)

if __name__ == "__main__":
    main()
