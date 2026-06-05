import os
import sys
import base64
import json
import uuid
import hashlib
from datetime import datetime, date

# Add the directory to python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.gcp.kms import encrypt_data
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
uri = os.getenv("MONGODB_URI")
print("Connecting to MongoDB Atlas...")
client = MongoClient(uri)
db = client["cliniqai"]
col = db["patients"]

phone = "9876543210"

# Delete any existing demo record for this phone number to prevent duplicates
col.delete_many({"phone": phone})

# Encrypt PII
encrypted_pii = encrypt_data({
    "name": "Priya Sharma",
    "age": 29,
    "gender": "Female"
})

# Build visits
visits = [
    {
        "visit_id": str(uuid.uuid4()),
        "date": "2026-05-12",
        "created_at": "2026-05-12T10:00:00Z",
        "doctor": "Dr. Sneha Patel",
        "clinic": "Lotus Medical Center",
        "diagnosis": ["Allergic Rhinitis"],
        "medicines": [
            {"name": "Cetirizine", "dose": "10mg", "frequency": "once daily at night", "duration": "10 days"}
        ],
        "tests": [],
        "notes": "Avoid cold foods. Known allergy to penicillin.",
        "source_document": None
    },
    {
        "visit_id": str(uuid.uuid4()),
        "date": "2026-05-22",
        "created_at": "2026-05-22T14:30:00Z",
        "doctor": "Dr. Sneha Patel",
        "clinic": "Lotus Medical Center",
        "diagnosis": ["Otitis Media"],
        "medicines": [
            {"name": "Amoxicillin", "dose": "500mg", "frequency": "thrice daily", "duration": "7 days"}
        ],
        "tests": [],
        "notes": "Triggers Penicillin Allergy conflict warning!",
        "source_document": None
    },
    {
        "visit_id": str(uuid.uuid4()),
        "date": "2026-06-02",
        "created_at": "2026-06-02T11:15:00Z",
        "doctor": "Dr. Amit Sharma",
        "clinic": "City General Clinic",
        "diagnosis": ["Acute Bronchitis"],
        "medicines": [
            {"name": "Paracetamol", "dose": "650mg", "frequency": "thrice daily", "duration": "3 days"},
            {"name": "Levosalbutamol Inhaler", "dose": "50mcg", "frequency": "as needed", "duration": "10 days"}
        ],
        "tests": ["Chest X-Ray"],
        "notes": "Patient reports throat irritation.",
        "source_document": None
    }
]

# Generate audit log chain
previous_hash = ""
audit_log = []

for idx, v in enumerate(visits):
    timestamp = v["created_at"]
    action = "PRESCRIPTION_UPLOADED"
    payload = {
        "timestamp": timestamp,
        "action": action,
        "doctor": v["doctor"],
        "ip_address": "127.0.0.1",
        "details": {
            "phone": phone,
            "visit_id": v["visit_id"],
            "duplicate_check": {"is_duplicate": False}
        }
    }
    serial = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    hash_val = hashlib.sha256(f"{previous_hash}|{serial}".encode("utf-8")).hexdigest()
    
    audit_event = {
        **payload,
        "previous_hash": previous_hash,
        "hash": hash_val
    }
    audit_log.append(audit_event)
    previous_hash = hash_val

# Patient Document
doc = {
    "patient_id": str(uuid.uuid4()),
    "phone": phone,
    "name": "[ENCRYPTED_KMS]",
    "age": "[ENCRYPTED_KMS]",
    "gender": "[ENCRYPTED_KMS]",
    "secure_pii": encrypted_pii,
    "known_allergies": ["penicillin"],
    "conditions": ["Allergic Rhinitis", "Otitis Media", "Acute Bronchitis"],
    "visits": visits,
    "audit_log": audit_log,
    "created_at": "2026-05-12T10:00:00Z"
}

col.insert_one(doc)
print(f"Successfully populated patient demo for phone {phone} (Priya Sharma) in MongoDB!")
