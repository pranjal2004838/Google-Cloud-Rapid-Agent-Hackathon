"""
CliniqAI — FastAPI Server (Phase 1 + Multi-Agent Orchestration)

Architecture: 1 Supervisor + 4 Specialized Agents
- ExtractionAgent: reads prescription images via Gemini on Vertex AI
- PatientContextAgent: retrieves patient history from MongoDB
- SafetyAgent: evaluates drug conflicts and allergy risks
- RecordUpdateAgent: persists records with audit trail

The /process and /test/process endpoints delegate to the Supervisor.
Other endpoints (query, patient lookup, recent, alerts) remain direct.
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


# Multi-agent orchestration
from agent.orchestration.supervisor import Supervisor
from agent.orchestration.agents.extraction_agent import ExtractionAgent
from agent.orchestration.agents.patient_context_agent import PatientContextAgent
from agent.orchestration.agents.safety_agent import SafetyAgent
from agent.orchestration.agents.record_update_agent import RecordUpdateAgent
from agent.orchestration.state import WorkflowStatus

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


# ─── Multi-Agent Supervisor Factory ──────────────────────────────────────────

def _create_supervisor() -> Supervisor:
    """Create a Supervisor instance with proper agent configuration."""
    use_mongo = get_db()
    db_col = patients_collection if use_mongo else None

    return Supervisor(
        extraction_agent=ExtractionAgent(),
        patient_context_agent=PatientContextAgent(
            db_collection=db_col,
            in_memory_store=in_memory_patients,
        ),
        safety_agent=SafetyAgent(),
        record_update_agent=RecordUpdateAgent(
            db_collection=db_col,
            in_memory_store=in_memory_patients,
        ),
    )


def _state_to_response(state) -> dict:
    """
    Convert WorkflowState to the existing API response shape.
    Preserves backward compatibility with the frontend.
    """
    extracted = state.extracted_data
    context = state.patient_context
    safety = state.safety_assessment
    write = state.write_result

    # Build confidence report in the old format
    confidence_scores = extracted.confidence_scores if extracted else {}
    low_fields = []
    threshold = 0.7
    for field, score in confidence_scores.items():
        if field.startswith("_"):
            continue
        if isinstance(score, (int, float)) and score < threshold:
            low_fields.append(field)
        elif isinstance(score, list):
            for i, item in enumerate(score):
                if isinstance(item, dict):
                    for k, v in item.items():
                        if isinstance(v, (int, float)) and v < threshold:
                            low_fields.append(f"{field}[{i}].{k}")
                elif isinstance(item, (int, float)) and item < threshold:
                    low_fields.append(f"{field}[{i}]")

    confidence_report = {
        "scores": confidence_scores,
        "low_confidence_fields": low_fields,
        "needs_review": len(low_fields) > 0,
        "threshold": threshold,
    }

    # Build patient payload
    medicines_with_conf = []
    if extracted:
        med_scores = confidence_scores.get("medicines", [])
        for i, med in enumerate(extracted.medicines):
            score_obj = med_scores[i] if i < len(med_scores) and isinstance(med_scores[i], dict) else {}
            medicines_with_conf.append({
                "name": med.name,
                "dose": med.dose,
                "frequency": med.frequency,
                "duration": med.duration,
                "_confidence": score_obj,
            })

    patient_payload = {
        "phone": state.request.phone,
        "name": extracted.patient_name if extracted else "Unknown",
        "age": extracted.patient_age if extracted else None,
        "gender": extracted.patient_gender if extracted else None,
        "doctor": extracted.doctor_name if extracted else None,
        "visit_date": (extracted.visit_date or str(date.today())) if extracted else str(date.today()),
        "diagnosis": extracted.diagnosis if extracted else [],
        "medicines": medicines_with_conf,
        "known_allergies": context.all_allergies if context else [],
        "visit_count": write.visit_count if write else 1,
        "_confidence": {
            "name": confidence_scores.get("patient_name"),
            "age": confidence_scores.get("patient_age"),
            "gender": confidence_scores.get("patient_gender"),
            "doctor": confidence_scores.get("doctor_name"),
            "visit_date": confidence_scores.get("visit_date"),
            "clinic": confidence_scores.get("clinic_name"),
            "diagnosis": confidence_scores.get("diagnosis"),
            "tests_ordered": confidence_scores.get("tests_ordered"),
            "allergies_mentioned": confidence_scores.get("allergies_mentioned"),
            "notes": confidence_scores.get("notes"),
        },
    }

    # Build audit section
    audit_section = {}
    if write and write.audit_event:
        audit_section = {
            "last_event": write.audit_event,
            "chain_valid": write.audit_chain_valid,
            "entries": write.audit_entries,
        }

    # Duplicate check
    duplicate_check = context.duplicate_check if context else {"is_duplicate": False}

    # Alerts
    alerts = []
    if safety:
        alerts = [a.model_dump() for a in safety.alerts]

    # Workflow trace (new field — bonus for judges)
    trace = [t.model_dump() for t in state.trace]

    return {
        "record_id": write.record_id if write else "",
        "is_returning": write.is_returning if write else False,
        "patient": patient_payload,
        "low_confidence_fields": low_fields,
        "confidence": confidence_report,
        "duplicate_check": duplicate_check,
        "audit": audit_section,
        "gcs_source_document": state.request.gcs_upload_result,
        "alerts": alerts,
        "workflow_status": state.status.value,
        "workflow_review_reason": state.review_reason,
        "workflow_trace": trace,
    }




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


# ─── Process Document (Main endpoint — Multi-Agent Orchestration) ────────────
@app.post("/process")
async def process_document(
    request: Request,
    phone: str = Form(...),  # Phone number from form (required)
    file: UploadFile = File(...)
):
    """
    Multi-agent prescription processing pipeline:
    1. Upload source document to Cloud Storage
    2. Supervisor orchestrates: Extraction → PatientContext → Safety → RecordUpdate
    3. Return structured result with alerts and workflow trace

    Args:
        phone: Patient's phone number (unique identifier)
        file: Prescription image file
    """
    # Read image bytes
    image_bytes = await file.read()

    # Upload source document to Cloud Storage (before agent pipeline)
    phone_clean = phone.strip().replace(" ", "")
    gcs_upload = upload_bytes_to_gcs(image_bytes, phone_clean, file.content_type)

    # Get client IP for audit
    ip_address = (request.client.host if request.client else None) or "unknown"

    # Run the multi-agent supervisor pipeline
    supervisor = _create_supervisor()
    state = await supervisor.run(
        phone=phone_clean,
        image_bytes=image_bytes,
        ip_address=ip_address,
        content_type=file.content_type,
        gcs_upload_result=gcs_upload,
    )

    # Check for hard failure
    if state.status == WorkflowStatus.FAILED:
        return {"error": state.error or "Processing failed", "workflow_trace": [t.model_dump() for t in state.trace]}

    # Convert state to API response (preserves existing frontend contract)
    return _state_to_response(state)


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


# ─── Test Endpoint (Multi-Agent with pre-extracted data) ─────────────────────
@app.post("/test/process")
async def test_process(data: dict):
    """
    Accepts pre-extracted data (skips Gemini extraction) and routes through
    the same multi-agent Supervisor pipeline.
    Send JSON like: {"phone": "9876543210", "patient_name": "Ramesh", "medicines": [...], ...}
    """
    phone = data.get("phone", "")
    phone_clean = phone.strip().replace(" ", "") if phone else ""

    # Run supervisor with extracted_override (skips ExtractionAgent's Gemini call)
    supervisor = _create_supervisor()
    state = await supervisor.run(
        phone=phone_clean,
        ip_address="test-client",
        gcs_upload_result=data.get("source_document"),
        extracted_override=data,
    )

    # Check for hard failure
    if state.status == WorkflowStatus.FAILED:
        return {"error": state.error or "Processing failed", "workflow_trace": [t.model_dump() for t in state.trace]}

    return _state_to_response(state)
