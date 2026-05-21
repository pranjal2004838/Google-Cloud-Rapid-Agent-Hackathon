"""
CliniqAI — FastAPI Server (Phase 1)

Simple backend that:
1. Accepts prescription image uploads
2. Extracts data using Gemini Vision (vision_tool)
3. Checks drug conflicts (alert_tool)
4. Stores/updates patient records in MongoDB
5. Answers natural language queries
"""

import os
import re
import uuid
import json
import hashlib
from datetime import datetime, date

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from dotenv import load_dotenv

from agent.tools.vision_tool import extract_from_prescription
from agent.tools.alert_tool import check_drug_conflicts, check_drug_conflicts_ai

# ─── Load environment variables ───────────────────────────────────────────────
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# ─── MongoDB Connection (lazy — gracefully handles missing config) ────────────
client = None
db = None
patients_collection = None


def get_db():
    """Connect to MongoDB on first use. Returns True if connected."""
    global client, db, patients_collection
    if patients_collection is not None:
        return True
    if not MONGODB_URI or "youruser" in MONGODB_URI:
        return False
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")  # Test connection
        db = client["cliniqai"]
        patients_collection = db["patients"]
        return True
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        return False

# ─── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(title="CliniqAI", version="1.0")

# Allow frontend to call this backend (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request Models ───────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: str


class ProcessRequest(BaseModel):
    """Request model for processing with phone number"""
    phone: str
    file: UploadFile = File(...)


# ─── In-Memory Store (fallback when MongoDB is not configured) ────────────────
# This lets you test the app without MongoDB. Records are lost on restart.
in_memory_patients = []


def clean_phone(phone: str) -> str:
    return phone.strip().replace(" ", "").replace("-", "")


def medicine_names(medicines: list) -> list:
    names = []
    for medicine in medicines:
        name = medicine.get("name", "") if isinstance(medicine, dict) else str(medicine)
        clean_name = name.strip().lower()
        if clean_name:
            names.append(clean_name)
    return names


def medicine_similarity(first: list, second: list) -> float:
    first_names = set(medicine_names(first))
    second_names = set(medicine_names(second))
    if not first_names and not second_names:
        return 1.0
    if not first_names or not second_names:
        return 0.0
    return len(first_names.intersection(second_names)) / len(first_names.union(second_names))


def find_duplicate_visit(existing_patient: dict, new_visit: dict) -> dict:
    if not existing_patient:
        return {"is_duplicate": False}
    new_date = new_visit.get("date")
    for index, old_visit in enumerate(existing_patient.get("visits", [])):
        same_date = old_visit.get("date") == new_date
        similarity = medicine_similarity(old_visit.get("medicines", []), new_visit.get("medicines", []))
        if same_date and similarity >= 0.9:
            return {
                "is_duplicate": True,
                "similarity": round(similarity, 2),
                "previous_visit_index": index,
                "message": "This prescription looks like a duplicate of an existing visit for the same phone number and date."
            }
    return {"is_duplicate": False}


def analyze_confidence(extracted: dict) -> dict:
    confidence = extracted.get("confidence", {})
    low_fields = []
    threshold = 0.7
    for field, score in confidence.items():
        if isinstance(score, list):
            for index, item_score in enumerate(score):
                if isinstance(item_score, (int, float)) and item_score < threshold:
                    low_fields.append(f"{field}[{index}]")
        elif isinstance(score, (int, float)) and score < threshold:
            low_fields.append(field)
    return {
        "scores": confidence,
        "low_confidence_fields": low_fields,
        "needs_review": len(low_fields) > 0,
        "threshold": threshold
    }


def make_audit_entry(action: str, phone: str, details: dict, previous_hash: str = "") -> dict:
    timestamp = datetime.now().isoformat()
    payload = {
        "timestamp": timestamp,
        "action": action,
        "phone": phone,
        "details": details,
        "previous_hash": previous_hash
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    payload["hash"] = hashlib.sha256(encoded).hexdigest()
    return payload


def last_audit_hash(patient: dict) -> str:
    if not patient:
        return ""
    audit_log = patient.get("audit_log", [])
    if not audit_log:
        return ""
    return audit_log[-1].get("hash", "")


# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    """Simple health check endpoint."""
    db_connected = get_db()
    if db_connected:
        mongo_status = "connected"
    else:
        mongo_status = "not configured (using in-memory store)"

    return {
        "status": "running",
        "mongodb": mongo_status,
        "google_api_key_set": bool(GOOGLE_API_KEY and "your_google" not in GOOGLE_API_KEY),
    }


# ─── Process Document (Main endpoint) ─────────────────────────────────────────
@app.post("/process")
async def process_document(
    phone: str = Form(...),  # Phone number from form (required)
    file: UploadFile = File(...)
):
    """
    1. Read uploaded image
    2. Extract patient data using Gemini Vision
    3. Check if patient already exists by PHONE NUMBER
    4. Insert or update patient record
    5. Run AI drug conflict check
    6. Return everything to the frontend
    
    Args:
        phone: Patient's phone number (unique identifier)
        file: Prescription image file
    """

    # Step 1: Read image bytes
    image_bytes = await file.read()

    # Step 2: Extract data from the prescription image
    extracted = extract_from_prescription(image_bytes)

    if "error" in extracted:
        return {"error": extracted["error"], "raw": extracted.get("raw_response", "")}

    # Step 3: Check if patient already exists by PHONE NUMBER
    patient_name = extracted.get("patient_name", "Unknown")
    phone_clean = clean_phone(phone)
    use_mongo = get_db()
    confidence_report = analyze_confidence(extracted)

    # Build the visit record from extracted data
    visit = {
        "date": extracted.get("visit_date", str(date.today())),
        "doctor": extracted.get("doctor_name"),
        "clinic": extracted.get("clinic_name"),
        "diagnosis": extracted.get("diagnosis", []),
        "medicines": extracted.get("medicines", []),
        "tests": extracted.get("tests_ordered", []),
        "notes": extracted.get("notes"),
    }

    is_returning = False
    patient_id = ""
    visit_count = 1
    patient_allergies = extracted.get("allergies_mentioned", [])
    current_medicines = []

    if use_mongo:
        # ── MongoDB path ──
        # Search by PHONE NUMBER (unique identifier) instead of name
        existing_patient = patients_collection.find_one({"phone": phone_clean})
        duplicate_check = find_duplicate_visit(existing_patient, visit)

        if existing_patient:
            is_returning = True
            existing_allergies = existing_patient.get("known_allergies", [])
            new_allergies = extracted.get("allergies_mentioned", [])
            all_allergies = list(set(existing_allergies + new_allergies))
            audit_entry = make_audit_entry(
                "DUPLICATE_PRESCRIPTION_BLOCKED" if duplicate_check["is_duplicate"] else "VISIT_ADDED",
                phone_clean,
                {
                    "patient_name": patient_name,
                    "duplicate_check": duplicate_check,
                    "low_confidence_fields": confidence_report["low_confidence_fields"]
                },
                last_audit_hash(existing_patient)
            )

            patients_collection.update_one(
                {"_id": existing_patient["_id"]},
                {
                    "$push": (
                        {"audit_log": audit_entry}
                        if duplicate_check["is_duplicate"]
                        else {"visits": visit, "audit_log": audit_entry}
                    ),
                    "$set": {"known_allergies": all_allergies}
                }
            )
            patient_id = str(existing_patient["_id"])
            visit_count = len(existing_patient.get("visits", [])) + (0 if duplicate_check["is_duplicate"] else 1)
            patient_allergies = all_allergies
            for prev_visit in existing_patient.get("visits", []):
                current_medicines.extend(prev_visit.get("medicines", []))
        else:
            audit_entry = make_audit_entry(
                "PATIENT_CREATED",
                phone_clean,
                {
                    "patient_name": patient_name,
                    "low_confidence_fields": confidence_report["low_confidence_fields"]
                }
            )
            patient_doc = {
                "patient_id": str(uuid.uuid4()),
                "phone": phone_clean,  # Store phone number as unique ID
                "name": patient_name,
                "age": extracted.get("patient_age"),
                "gender": extracted.get("patient_gender"),
                "known_allergies": extracted.get("allergies_mentioned", []),
                "conditions": extracted.get("diagnosis", []),
                "visits": [visit],
                "audit_log": [audit_entry],
                "created_at": datetime.now().isoformat(),
            }
            result = patients_collection.insert_one(patient_doc)
            patient_id = str(result.inserted_id)
    else:
        # ── In-memory fallback ──
        existing_patient = next((p for p in in_memory_patients if p.get("phone") == phone_clean), None)
        duplicate_check = find_duplicate_visit(existing_patient, visit)

        if existing_patient:
            is_returning = True
            existing_allergies = existing_patient.get("known_allergies", [])
            new_allergies = extracted.get("allergies_mentioned", [])
            all_allergies = list(set(existing_allergies + new_allergies))
            existing_patient["known_allergies"] = all_allergies
            audit_entry = make_audit_entry(
                "DUPLICATE_PRESCRIPTION_BLOCKED" if duplicate_check["is_duplicate"] else "VISIT_ADDED",
                phone_clean,
                {
                    "patient_name": patient_name,
                    "duplicate_check": duplicate_check,
                    "low_confidence_fields": confidence_report["low_confidence_fields"]
                },
                last_audit_hash(existing_patient)
            )
            existing_patient.setdefault("audit_log", []).append(audit_entry)
            if not duplicate_check["is_duplicate"]:
                existing_patient["visits"].append(visit)
            patient_id = existing_patient["patient_id"]
            visit_count = len(existing_patient["visits"])
            patient_allergies = all_allergies
            for prev_visit in existing_patient["visits"][:-1]:
                current_medicines.extend(prev_visit.get("medicines", []))
        else:
            audit_entry = make_audit_entry(
                "PATIENT_CREATED",
                phone_clean,
                {
                    "patient_name": patient_name,
                    "low_confidence_fields": confidence_report["low_confidence_fields"]
                }
            )
            patient_doc = {
                "patient_id": str(uuid.uuid4()),
                "phone": phone_clean,  # Store phone number as unique ID
                "name": patient_name,
                "age": extracted.get("patient_age"),
                "gender": extracted.get("patient_gender"),
                "known_allergies": extracted.get("allergies_mentioned", []),
                "conditions": extracted.get("diagnosis", []),
                "visits": [visit],
                "audit_log": [audit_entry],
                "created_at": datetime.now().isoformat(),
            }
            in_memory_patients.append(patient_doc)
            patient_id = patient_doc["patient_id"]

    # Step 5: Run AI-powered drug conflict check
    new_medicines = extracted.get("medicines", [])
    
    # Use AI-powered checker (falls back to rule-based if no API key)
    conflict_result = check_drug_conflicts_ai(
        patient_allergies=patient_allergies,
        current_medicines=current_medicines,
        new_medicines=new_medicines,
    )

    # Step 6: Return the result to the frontend
    return {
        "record_id": patient_id,
        "is_returning": is_returning,
        "patient": {
            "phone": phone_clean,
            "name": patient_name,
            "age": extracted.get("patient_age"),
            "gender": extracted.get("patient_gender"),
            "doctor": extracted.get("doctor_name"),
            "visit_date": extracted.get("visit_date", str(date.today())),
            "diagnosis": extracted.get("diagnosis", []),
            "medicines": new_medicines,
            "known_allergies": patient_allergies,
            "visit_count": visit_count,
        },
        "confidence": confidence_report,
        "duplicate_check": duplicate_check,
        "alerts": conflict_result["alerts"],
    }


# ─── Query Endpoint ───────────────────────────────────────────────────────────
@app.post("/query")
async def run_query(request: QueryRequest):
    """
    Simple natural language query handler.
    For Phase 1, we do basic keyword matching.
    """
    query = request.query.lower()
    use_mongo = get_db()

    if use_mongo:
        # ── MongoDB queries ──
        if "how many" in query or "count" in query:
            count = patients_collection.count_documents({})
            return {"answer": f"Total patients in database: {count}"}

        elif "diabetic" in query or "diabetes" in query:
            patients = list(patients_collection.find({"conditions": {"$regex": "diabet", "$options": "i"}}))
            if patients:
                return {"answer": f"Found {len(patients)} diabetic patient(s): {', '.join(p['name'] for p in patients)}"}
            return {"answer": "No diabetic patients found."}

        else:
            # Try to search by phone, name, medicine, or condition
            safe_query = re.escape(query)  # Escape regex special chars from user input
            patients = list(patients_collection.find({"$or": [
                {"phone": {"$regex": safe_query, "$options": "i"}},
                {"name": {"$regex": safe_query, "$options": "i"}},
                {"conditions": {"$regex": safe_query, "$options": "i"}},
                {"visits.medicines.name": {"$regex": safe_query, "$options": "i"}},
            ]}))
            if patients:
                return {"answer": f"Found {len(patients)} result(s): {', '.join(p['name'] for p in patients)}"}
            return {"answer": "No results found. Try searching by patient name, medicine, or condition."}

    else:
        # ── In-memory search ──
        if "how many" in query or "count" in query:
            return {"answer": f"Total patients in database: {len(in_memory_patients)}"}

        # Search in memory
        results = []
        for p in in_memory_patients:
            name_match = query in p["name"].lower()
            condition_match = any(query in c.lower() for c in p.get("conditions", []))
            med_match = any(
                query in m.get("name", "").lower()
                for v in p.get("visits", [])
                for m in v.get("medicines", [])
            )
            if name_match or condition_match or med_match:
                results.append(p)

        if results:
            return {"answer": f"Found {len(results)} result(s): {', '.join(p['name'] for p in results)}"}
        return {"answer": "No results found. Try searching by patient name, medicine, or condition."}


# ─── Get Patient by Phone ─────────────────────────────────────────────────────
@app.get("/patient/{phone}")
async def get_patient_by_phone(phone: str):
    """Get a single patient by their phone number."""
    use_mongo = get_db()
    phone_clean = phone.strip().replace(" ", "")
    
    if use_mongo:
        patient = patients_collection.find_one({"phone": phone_clean})
        if patient:
            # Remove MongoDB's internal _id for cleaner JSON
            patient.pop("_id", None)
            return {"found": True, "patient": patient}
        return {"found": False, "message": "Patient not found"}
    else:
        patient = next((p for p in in_memory_patients if p.get("phone") == phone_clean), None)
        if patient:
            return {"found": True, "patient": patient}
        return {"found": False, "message": "Patient not found"}


# ─── Recent Patients ──────────────────────────────────────────────────────────
@app.get("/recent")
async def get_recent_patients():
    """Returns the 10 most recently added patients."""
    use_mongo = get_db()

    if use_mongo:
        results = patients_collection.find().sort("created_at", -1).limit(10)
        patients = []
        for p in results:
            patients.append({
                "phone": p.get("phone", ""),
                "name": p.get("name", "Unknown"),
                "conditions": p.get("conditions", []),
                "has_alerts": len(p.get("known_allergies", [])) > 0,
            })
    else:
        patients = []
        for p in in_memory_patients[-10:]:
            patients.append({
                "phone": p.get("phone", ""),
                "name": p.get("name", "Unknown"),
                "conditions": p.get("conditions", []),
                "has_alerts": len(p.get("known_allergies", [])) > 0,
            })

    return {"patients": patients}


# ─── Test Endpoint (simulate processing without Gemini API) ──────────────────
@app.post("/test/process")
async def test_process(data: dict):
    """
    Accepts pre-extracted data (skips Gemini Vision) for testing.
    Send JSON like: {"phone": "9876543210", "patient_name": "Ramesh", "medicines": [...], ...}
    """
    extracted = data
    patient_name = extracted.get("patient_name", "Unknown")
    phone = extracted.get("phone", "")
    phone_clean = clean_phone(phone) if phone else ""
    use_mongo = get_db()
    confidence_report = analyze_confidence(extracted)

    visit = {
        "date": extracted.get("visit_date", str(date.today())),
        "doctor": extracted.get("doctor_name"),
        "clinic": extracted.get("clinic_name"),
        "diagnosis": extracted.get("diagnosis", []),
        "medicines": extracted.get("medicines", []),
        "tests": extracted.get("tests_ordered", []),
        "notes": extracted.get("notes"),
    }

    is_returning = False
    patient_id = ""
    visit_count = 1
    patient_allergies = extracted.get("allergies_mentioned", [])
    current_medicines = []
    duplicate_check = {"is_duplicate": False}

    if use_mongo:
        existing_patient = patients_collection.find_one({"phone": phone_clean}) if phone_clean else None
        duplicate_check = find_duplicate_visit(existing_patient, visit)
        if existing_patient:
            is_returning = True
            all_allergies = list(set(existing_patient.get("known_allergies", []) + extracted.get("allergies_mentioned", [])))
            audit_entry = make_audit_entry(
                "DUPLICATE_PRESCRIPTION_BLOCKED" if duplicate_check["is_duplicate"] else "VISIT_ADDED",
                phone_clean,
                {
                    "patient_name": patient_name,
                    "duplicate_check": duplicate_check,
                    "low_confidence_fields": confidence_report["low_confidence_fields"]
                },
                last_audit_hash(existing_patient)
            )
            patients_collection.update_one(
                {"_id": existing_patient["_id"]},
                {
                    "$push": (
                        {"audit_log": audit_entry}
                        if duplicate_check["is_duplicate"]
                        else {"visits": visit, "audit_log": audit_entry}
                    ),
                    "$set": {"known_allergies": all_allergies}
                }
            )
            patient_id = str(existing_patient["_id"])
            visit_count = len(existing_patient.get("visits", [])) + (0 if duplicate_check["is_duplicate"] else 1)
            patient_allergies = all_allergies
            for prev_visit in existing_patient.get("visits", []):
                current_medicines.extend(prev_visit.get("medicines", []))
        else:
            audit_entry = make_audit_entry(
                "PATIENT_CREATED",
                phone_clean,
                {
                    "patient_name": patient_name,
                    "low_confidence_fields": confidence_report["low_confidence_fields"]
                }
            )
            patient_doc = {
                "patient_id": str(uuid.uuid4()),
                "phone": phone_clean,
                "name": patient_name,
                "age": extracted.get("patient_age"),
                "gender": extracted.get("patient_gender"),
                "known_allergies": extracted.get("allergies_mentioned", []),
                "conditions": extracted.get("diagnosis", []),
                "visits": [visit],
                "audit_log": [audit_entry],
                "created_at": datetime.now().isoformat(),
            }
            result = patients_collection.insert_one(patient_doc)
            patient_id = str(result.inserted_id)
    else:
        existing_patient = next((p for p in in_memory_patients if p.get("phone") == phone_clean), None) if phone_clean else None
        duplicate_check = find_duplicate_visit(existing_patient, visit)
        if existing_patient:
            is_returning = True
            all_allergies = list(set(existing_patient.get("known_allergies", []) + extracted.get("allergies_mentioned", [])))
            existing_patient["known_allergies"] = all_allergies
            audit_entry = make_audit_entry(
                "DUPLICATE_PRESCRIPTION_BLOCKED" if duplicate_check["is_duplicate"] else "VISIT_ADDED",
                phone_clean,
                {
                    "patient_name": patient_name,
                    "duplicate_check": duplicate_check,
                    "low_confidence_fields": confidence_report["low_confidence_fields"]
                },
                last_audit_hash(existing_patient)
            )
            existing_patient.setdefault("audit_log", []).append(audit_entry)
            if not duplicate_check["is_duplicate"]:
                existing_patient["visits"].append(visit)
            patient_id = existing_patient["patient_id"]
            visit_count = len(existing_patient["visits"])
            patient_allergies = all_allergies
            for prev_visit in existing_patient["visits"][:-1]:
                current_medicines.extend(prev_visit.get("medicines", []))
        else:
            audit_entry = make_audit_entry(
                "PATIENT_CREATED",
                phone_clean,
                {
                    "patient_name": patient_name,
                    "low_confidence_fields": confidence_report["low_confidence_fields"]
                }
            )
            patient_doc = {
                "patient_id": str(uuid.uuid4()),
                "phone": phone_clean,
                "name": patient_name,
                "age": extracted.get("patient_age"),
                "gender": extracted.get("patient_gender"),
                "known_allergies": extracted.get("allergies_mentioned", []),
                "conditions": extracted.get("diagnosis", []),
                "visits": [visit],
                "audit_log": [audit_entry],
                "created_at": datetime.now().isoformat(),
            }
            in_memory_patients.append(patient_doc)
            patient_id = patient_doc["patient_id"]

    new_medicines = extracted.get("medicines", [])
    conflict_result = check_drug_conflicts_ai(
        patient_allergies=patient_allergies,
        current_medicines=current_medicines,
        new_medicines=new_medicines,
    )

    return {
        "record_id": patient_id,
        "is_returning": is_returning,
        "patient": {
            "phone": phone_clean,
            "name": patient_name,
            "age": extracted.get("patient_age"),
            "gender": extracted.get("patient_gender"),
            "doctor": extracted.get("doctor_name"),
            "visit_date": extracted.get("visit_date", str(date.today())),
            "diagnosis": extracted.get("diagnosis", []),
            "medicines": new_medicines,
            "known_allergies": patient_allergies,
            "visit_count": visit_count,
        },
        "confidence": confidence_report,
        "duplicate_check": duplicate_check,
        "alerts": conflict_result["alerts"],
    }

