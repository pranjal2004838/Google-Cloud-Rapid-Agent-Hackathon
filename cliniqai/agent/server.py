"""
CliniqAI — FastAPI Server (Phase 1)

Simple backend that:
1. Accepts prescription image uploads
2. Stores uploaded source document in Cloud Storage (if configured)
3. Extracts data using Gemini on Vertex AI (vision_tool)
4. Checks drug conflicts (alert_tool)
5. Stores/updates patient records in MongoDB
6. Answers natural language queries
"""

import os
import re
import uuid
import json
import hashlib
from datetime import datetime, date, timedelta
from uuid import uuid4

from fastapi import FastAPI, UploadFile, File, Form, Request
from google.cloud import storage
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from dotenv import load_dotenv

from agent.tools.vision_tool import extract_from_prescription
from agent.tools.alert_tool import check_drug_conflicts, check_drug_conflicts_ai

# ─── Load environment variables ───────────────────────────────────────────────
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
GCS_UPLOAD_BUCKET = os.getenv("GCS_UPLOAD_BUCKET")

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


class AlertAcknowledgeRequest(BaseModel):
    phone: str
    alert: str
    override_reason: str
    doctor_name: str | None = None


class ProcessRequest(BaseModel):
    """Request model for processing with phone number"""
    phone: str
    file: UploadFile = File(...)


# ─── In-Memory Store (fallback when MongoDB is not configured) ────────────────
# This lets you test the app without MongoDB. Records are lost on restart.
in_memory_patients = []




def upload_bytes_to_gcs(image_bytes: bytes, phone: str, content_type: str | None = None) -> dict | None:
    """Upload raw document bytes to Cloud Storage and return object metadata."""
    if not GCS_UPLOAD_BUCKET:
        return None

    if not GOOGLE_CLOUD_PROJECT or "your_project" in GOOGLE_CLOUD_PROJECT:
        return None

    mime = content_type or "application/octet-stream"
    extension = ".jpg"
    if mime == "image/png":
        extension = ".png"
    elif mime == "application/pdf":
        extension = ".pdf"

    object_name = f"prescriptions/{phone}/{datetime.utcnow().strftime('%Y%m%d')}/{uuid4().hex}{extension}"

    try:
        client = storage.Client(project=GOOGLE_CLOUD_PROJECT)
        bucket = client.bucket(GCS_UPLOAD_BUCKET)
        blob = bucket.blob(object_name)
        blob.upload_from_string(image_bytes, content_type=mime)
        return {
            "bucket": GCS_UPLOAD_BUCKET,
            "object": object_name,
            "uri": f"gs://{GCS_UPLOAD_BUCKET}/{object_name}",
            "content_type": mime,
        }
    except Exception as exc:
        # Non-fatal in Phase 1: extraction can continue even if storage upload fails.
        return {"error": f"Cloud Storage upload failed: {exc}"}


def _utc_now_iso() -> str:
    """Return current UTC timestamp in ISO format with trailing Z."""
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _normalize_med_name(med: dict) -> str:
    return (med.get("name") or "").strip().lower()


def _medicine_similarity(existing_medicines: list, new_medicines: list) -> float:
    """
    Compare two medicine lists using normalized name overlap.
    Returns 0.0–1.0 where 1.0 is identical.
    """
    existing_names = {name for name in (_normalize_med_name(m) for m in existing_medicines) if name}
    new_names = {name for name in (_normalize_med_name(m) for m in new_medicines) if name}
    if not existing_names and not new_names:
        return 1.0
    if not existing_names or not new_names:
        return 0.0
    overlap = len(existing_names.intersection(new_names))
    return overlap / max(len(existing_names), len(new_names))


def _visit_datetime(visit: dict) -> datetime:
    """
    Parse visit datetime from `created_at` or `date`; returns datetime.min on failure.
    """
    created_at = visit.get("created_at")
    if isinstance(created_at, str) and created_at:
        try:
            return datetime.fromisoformat(created_at.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            pass

    visit_date = visit.get("date")
    if isinstance(visit_date, str) and visit_date:
        try:
            return datetime.fromisoformat(visit_date)
        except Exception:
            pass

    return datetime.min


def find_duplicate_visit(visits: list, new_medicines: list, threshold: float = 0.95) -> dict:
    """
    Find likely duplicate from visits within last 7 days based on medicine similarity.
    Returns duplicate metadata or `{"is_duplicate": False}`.
    """
    now = datetime.utcnow()
    window_start = now - timedelta(days=7)
    best_match = None

    for visit in visits:
        visit_time = _visit_datetime(visit)
        if visit_time < window_start:
            continue
        similarity = _medicine_similarity(visit.get("medicines", []), new_medicines)
        if similarity >= threshold and (best_match is None or similarity > best_match["similarity"]):
            best_match = {"visit": visit, "similarity": similarity, "visit_time": visit_time}

    if best_match is None:
        return {"is_duplicate": False}

    delta = now - best_match["visit_time"]
    hours = max(1, int(delta.total_seconds() // 3600))
    return {
        "is_duplicate": True,
        "previous_visit_id": best_match["visit"].get("visit_id", "unknown"),
        "time_diff": f"{hours} hour(s) ago",
        "similarity": round(best_match["similarity"], 3),
        "warning": "This looks like a duplicate prescription. Please verify before saving.",
    }


def _audit_hash(payload: dict, previous_hash: str) -> str:
    serial = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{previous_hash}|{serial}".encode("utf-8")).hexdigest()


def build_audit_event(action: str, doctor: str, ip_address: str, details: dict, previous_hash: str = "") -> dict:
    timestamp = _utc_now_iso()
    payload = {
        "timestamp": timestamp,
        "action": action,
        "doctor": doctor or "Unknown",
        "ip_address": ip_address or "unknown",
        "details": details or {},
    }
    return {
        **payload,
        "previous_hash": previous_hash or "",
        "hash": _audit_hash(payload, previous_hash or ""),
    }


def verify_audit_chain(audit_log: list) -> bool:
    """Verify hash-chain integrity for audit entries."""
    previous_hash = ""
    for entry in audit_log:
        payload = {
            "timestamp": entry.get("timestamp"),
            "action": entry.get("action"),
            "doctor": entry.get("doctor"),
            "ip_address": entry.get("ip_address"),
            "details": entry.get("details", {}),
        }
        if entry.get("previous_hash", "") != previous_hash:
            return False
        if entry.get("hash") != _audit_hash(payload, previous_hash):
            return False
        previous_hash = entry.get("hash", "")
    return True


def analyze_confidence(extracted: dict, threshold: float = 0.7) -> dict:
    """
    Build a normalized confidence report from extraction output.
    Supports scalar scores and per-medicine score objects.
    """
    confidence = extracted.get("confidence", {})
    low_fields = []

    for field, score in confidence.items():
        if field == "medicines" and isinstance(score, list):
            for index, med_scores in enumerate(score):
                if isinstance(med_scores, dict):
                    for med_field, med_score in med_scores.items():
                        if isinstance(med_score, (int, float)) and med_score < threshold:
                            low_fields.append(f"medicines[{index}].{med_field}")
                elif isinstance(med_scores, (int, float)) and med_scores < threshold:
                    low_fields.append(f"medicines[{index}]")
        elif isinstance(score, list):
            for index, item_score in enumerate(score):
                if isinstance(item_score, (int, float)) and item_score < threshold:
                    low_fields.append(f"{field}[{index}]")
        elif isinstance(score, (int, float)) and score < threshold:
            low_fields.append(field)

    return {
        "scores": confidence,
        "low_confidence_fields": low_fields,
        "needs_review": len(low_fields) > 0,
        "threshold": threshold,
    }


def build_patient_confidence_payload(extracted: dict, confidence_report: dict) -> dict:
    """
    Build patient payload with confidence metadata that UI can highlight.
    """
    scores = confidence_report.get("scores", {})
    medicines = extracted.get("medicines", [])
    med_scores = scores.get("medicines", []) if isinstance(scores.get("medicines", []), list) else []
    medicines_with_confidence = []
    for i, med in enumerate(medicines):
        score_obj = med_scores[i] if i < len(med_scores) and isinstance(med_scores[i], dict) else {}
        medicines_with_confidence.append({
            **med,
            "_confidence": score_obj,
        })

    return {
        "phone": extracted.get("phone", ""),
        "name": extracted.get("patient_name", "Unknown"),
        "age": extracted.get("patient_age"),
        "gender": extracted.get("patient_gender"),
        "doctor": extracted.get("doctor_name"),
        "visit_date": extracted.get("visit_date", str(date.today())),
        "diagnosis": extracted.get("diagnosis", []),
        "medicines": medicines_with_confidence,
        "known_allergies": extracted.get("allergies_mentioned", []),
        "_confidence": {
            "name": scores.get("patient_name"),
            "age": scores.get("patient_age"),
            "gender": scores.get("patient_gender"),
            "doctor": scores.get("doctor_name"),
            "visit_date": scores.get("visit_date"),
            "clinic": scores.get("clinic_name"),
            "diagnosis": scores.get("diagnosis"),
            "tests_ordered": scores.get("tests_ordered"),
            "allergies_mentioned": scores.get("allergies_mentioned"),
            "notes": scores.get("notes"),
        },
    }


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
        "google_cloud_project_set": bool(GOOGLE_CLOUD_PROJECT and "your_project" not in GOOGLE_CLOUD_PROJECT),
        "google_cloud_location": GOOGLE_CLOUD_LOCATION,
        "gcs_upload_bucket_set": bool(GCS_UPLOAD_BUCKET),
    }


# ─── Process Document (Main endpoint) ─────────────────────────────────────────
@app.post("/process")
async def process_document(
    request: Request,
    phone: str = Form(...),  # Phone number from form (required)
    file: UploadFile = File(...)
):
    """
    1. Read uploaded image
    2. Upload source document to Cloud Storage (if configured)
    3. Extract patient data using Gemini on Vertex AI
    4. Check if patient already exists by PHONE NUMBER
    5. Insert or update patient record
    6. Run AI drug conflict check
    7. Return everything to the frontend
    
    Args:
        phone: Patient's phone number (unique identifier)
        file: Prescription image file
    """

    # Step 1: Read image bytes
    image_bytes = await file.read()

    # Step 2: Upload source document to Cloud Storage (Google-native ingestion)
    phone_clean = phone.strip().replace(" ", "")  # Clean phone number
    gcs_upload = upload_bytes_to_gcs(image_bytes, phone_clean, file.content_type)

    # Step 3: Extract data from the prescription image
    extracted = extract_from_prescription(image_bytes)

    if "error" in extracted:
        return {"error": extracted["error"], "raw": extracted.get("raw_response", "")}

    # Step 4: Check if patient already exists by PHONE NUMBER
    patient_name = extracted.get("patient_name", "Unknown")
    extracted["phone"] = phone_clean
    use_mongo = get_db()
    confidence_report = analyze_confidence(extracted)
    new_medicines = extracted.get("medicines", [])
    doctor_name = extracted.get("doctor_name")
    ip_address = (request.client.host if request.client else None) or "unknown"

    visit = {
        "visit_id": str(uuid.uuid4()),
        "date": extracted.get("visit_date", str(date.today())),
        "created_at": _utc_now_iso(),
        "doctor": doctor_name,
        "clinic": extracted.get("clinic_name"),
        "diagnosis": extracted.get("diagnosis", []),
        "medicines": new_medicines,
        "tests": extracted.get("tests_ordered", []),
        "notes": extracted.get("notes"),
        "source_document": gcs_upload if gcs_upload else None,
    }

    is_returning = False
    patient_id = ""
    visit_count = 1
    patient_allergies = extracted.get("allergies_mentioned", [])
    current_medicines = []
    duplicate_check = {"is_duplicate": False}
    audit_log_preview = []

    existing_patient = None
    if use_mongo:
        existing_patient = patients_collection.find_one({"phone": phone_clean})
    else:
        existing_patient = next((p for p in in_memory_patients if p.get("phone") == phone_clean), None)

    if existing_patient:
        is_returning = True
        duplicate_check = find_duplicate_visit(existing_patient.get("visits", []), new_medicines)
        existing_allergies = existing_patient.get("known_allergies", [])
        new_allergies = extracted.get("allergies_mentioned", [])
        all_allergies = list(set(existing_allergies + new_allergies))
        patient_allergies = all_allergies

        for prev_visit in existing_patient.get("visits", []):
            current_medicines.extend(prev_visit.get("medicines", []))

        previous_hash = (existing_patient.get("audit_log", [])[-1].get("hash", "")
                         if existing_patient.get("audit_log") else "")
        event_details = {
            "phone": phone_clean,
            "visit_id": visit["visit_id"],
            "duplicate_check": duplicate_check,
        }
        upload_event = build_audit_event(
            action="PRESCRIPTION_UPLOADED",
            doctor=doctor_name,
            ip_address=ip_address,
            details=event_details,
            previous_hash=previous_hash,
        )
        audit_log_preview = existing_patient.get("audit_log", []) + [upload_event]

        if use_mongo:
            patients_collection.update_one(
                {"_id": existing_patient["_id"]},
                {
                    "$push": {"visits": visit, "audit_log": upload_event},
                    "$set": {"known_allergies": all_allergies},
                },
            )
            patient_id = str(existing_patient["_id"])
            visit_count = len(existing_patient.get("visits", [])) + 1
        else:
            existing_patient["known_allergies"] = all_allergies
            existing_patient["visits"].append(visit)
            existing_patient.setdefault("audit_log", []).append(upload_event)
            patient_id = existing_patient["patient_id"]
            visit_count = len(existing_patient["visits"])
            audit_log_preview = existing_patient.get("audit_log", [])
    else:
        upload_event = build_audit_event(
            action="PRESCRIPTION_UPLOADED",
            doctor=doctor_name,
            ip_address=ip_address,
            details={"phone": phone_clean, "visit_id": visit["visit_id"], "duplicate_check": duplicate_check},
            previous_hash="",
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
            "audit_log": [upload_event],
            "created_at": datetime.now().isoformat(),
        }
        audit_log_preview = [upload_event]
        if use_mongo:
            result = patients_collection.insert_one(patient_doc)
            patient_id = str(result.inserted_id)
        else:
            in_memory_patients.append(patient_doc)
            patient_id = patient_doc["patient_id"]

    # Step 5: Run AI-powered drug conflict check
    conflict_result = check_drug_conflicts_ai(
        patient_allergies=patient_allergies,
        current_medicines=current_medicines,
        new_medicines=new_medicines,
    )

    patient_payload = build_patient_confidence_payload(extracted, confidence_report)
    patient_payload["known_allergies"] = patient_allergies
    patient_payload["visit_count"] = visit_count

    # Step 6: Return the result to the frontend
    return {
        "record_id": patient_id,
        "is_returning": is_returning,
        "patient": patient_payload,
        "low_confidence_fields": confidence_report["low_confidence_fields"],
        "confidence": confidence_report,
        "duplicate_check": duplicate_check,
        "audit": {
            "last_event": audit_log_preview[-1] if audit_log_preview else None,
            "chain_valid": verify_audit_chain(audit_log_preview),
            "entries": len(audit_log_preview),
        },
        "gcs_source_document": gcs_upload,
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


@app.post("/alerts/acknowledge")
async def acknowledge_alert(request: Request, payload: AlertAcknowledgeRequest):
    """
    Record immutable audit event when doctor acknowledges/overrides an alert.
    """
    phone_clean = payload.phone.strip().replace(" ", "")
    use_mongo = get_db()
    ip_address = (request.client.host if request.client else None) or "unknown"

    if use_mongo:
        patient = patients_collection.find_one({"phone": phone_clean})
        if not patient:
            return {"ok": False, "message": "Patient not found"}
        previous_hash = (patient.get("audit_log", [])[-1].get("hash", "") if patient.get("audit_log") else "")
        event = build_audit_event(
            action="ALERT_ACKNOWLEDGED",
            doctor=payload.doctor_name,
            ip_address=ip_address,
            details={"alert": payload.alert, "override_reason": payload.override_reason},
            previous_hash=previous_hash,
        )
        patients_collection.update_one({"_id": patient["_id"]}, {"$push": {"audit_log": event}})
        audit_log = patient.get("audit_log", []) + [event]
    else:
        patient = next((p for p in in_memory_patients if p.get("phone") == phone_clean), None)
        if not patient:
            return {"ok": False, "message": "Patient not found"}
        previous_hash = (patient.get("audit_log", [])[-1].get("hash", "") if patient.get("audit_log") else "")
        event = build_audit_event(
            action="ALERT_ACKNOWLEDGED",
            doctor=payload.doctor_name,
            ip_address=ip_address,
            details={"alert": payload.alert, "override_reason": payload.override_reason},
            previous_hash=previous_hash,
        )
        patient.setdefault("audit_log", []).append(event)
        audit_log = patient.get("audit_log", [])

    return {
        "ok": True,
        "event": event,
        "audit_entries": len(audit_log),
        "chain_valid": verify_audit_chain(audit_log),
    }


# ─── Test Endpoint (simulate processing without Gemini API) ──────────────────
@app.post("/test/process")
async def test_process(data: dict):
    """
    Accepts pre-extracted data (skips Gemini on Vertex AI extraction) for testing.
    Send JSON like: {"phone": "9876543210", "patient_name": "Ramesh", "medicines": [...], ...}
    """
    extracted = data
    patient_name = extracted.get("patient_name", "Unknown")
    phone = extracted.get("phone", "")
    phone_clean = phone.strip().replace(" ", "") if phone else ""
    extracted["phone"] = phone_clean
    gcs_upload = extracted.get("source_document")
    use_mongo = get_db()
    confidence_report = analyze_confidence(extracted)
    new_medicines = extracted.get("medicines", [])
    doctor_name = extracted.get("doctor_name")

    visit = {
        "visit_id": str(uuid.uuid4()),
        "date": extracted.get("visit_date", str(date.today())),
        "created_at": _utc_now_iso(),
        "doctor": doctor_name,
        "clinic": extracted.get("clinic_name"),
        "diagnosis": extracted.get("diagnosis", []),
        "medicines": new_medicines,
        "tests": extracted.get("tests_ordered", []),
        "notes": extracted.get("notes"),
        "source_document": gcs_upload if gcs_upload else None,
    }

    is_returning = False
    patient_id = ""
    visit_count = 1
    patient_allergies = extracted.get("allergies_mentioned", [])
    current_medicines = []
    duplicate_check = {"is_duplicate": False}
    audit_log_preview = []

    existing_patient = None
    if use_mongo and phone_clean:
        existing_patient = patients_collection.find_one({"phone": phone_clean})
    elif phone_clean:
        existing_patient = next((p for p in in_memory_patients if p.get("phone") == phone_clean), None)

    if existing_patient:
        is_returning = True
        duplicate_check = find_duplicate_visit(existing_patient.get("visits", []), new_medicines)
        all_allergies = list(set(existing_patient.get("known_allergies", []) + extracted.get("allergies_mentioned", [])))
        patient_allergies = all_allergies
        for prev_visit in existing_patient.get("visits", []):
            current_medicines.extend(prev_visit.get("medicines", []))

        previous_hash = (existing_patient.get("audit_log", [])[-1].get("hash", "")
                         if existing_patient.get("audit_log") else "")
        upload_event = build_audit_event(
            action="PRESCRIPTION_UPLOADED",
            doctor=doctor_name,
            ip_address="test-client",
            details={"phone": phone_clean, "visit_id": visit["visit_id"], "duplicate_check": duplicate_check},
            previous_hash=previous_hash,
        )
        audit_log_preview = existing_patient.get("audit_log", []) + [upload_event]

        if use_mongo:
            patients_collection.update_one(
                {"_id": existing_patient["_id"]},
                {
                    "$push": {"visits": visit, "audit_log": upload_event},
                    "$set": {"known_allergies": all_allergies},
                },
            )
            patient_id = str(existing_patient["_id"])
            visit_count = len(existing_patient.get("visits", [])) + 1
        else:
            existing_patient["known_allergies"] = all_allergies
            existing_patient["visits"].append(visit)
            existing_patient.setdefault("audit_log", []).append(upload_event)
            patient_id = existing_patient["patient_id"]
            visit_count = len(existing_patient["visits"])
            audit_log_preview = existing_patient.get("audit_log", [])
    else:
        upload_event = build_audit_event(
            action="PRESCRIPTION_UPLOADED",
            doctor=doctor_name,
            ip_address="test-client",
            details={"phone": phone_clean, "visit_id": visit["visit_id"], "duplicate_check": duplicate_check},
            previous_hash="",
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
            "audit_log": [upload_event],
            "created_at": datetime.now().isoformat(),
        }
        audit_log_preview = [upload_event]
        if use_mongo:
            result = patients_collection.insert_one(patient_doc)
            patient_id = str(result.inserted_id)
        else:
            in_memory_patients.append(patient_doc)
            patient_id = patient_doc["patient_id"]

    conflict_result = check_drug_conflicts_ai(
        patient_allergies=patient_allergies,
        current_medicines=current_medicines,
        new_medicines=new_medicines,
    )

    patient_payload = build_patient_confidence_payload(extracted, confidence_report)
    patient_payload["known_allergies"] = patient_allergies
    patient_payload["visit_count"] = visit_count

    return {
        "record_id": patient_id,
        "is_returning": is_returning,
        "patient": patient_payload,
        "low_confidence_fields": confidence_report["low_confidence_fields"],
        "confidence": confidence_report,
        "duplicate_check": duplicate_check,
        "audit": {
            "last_event": audit_log_preview[-1] if audit_log_preview else None,
            "chain_valid": verify_audit_chain(audit_log_preview),
            "entries": len(audit_log_preview),
        },
        "gcs_source_document": gcs_upload,
        "alerts": conflict_result["alerts"],
    }
