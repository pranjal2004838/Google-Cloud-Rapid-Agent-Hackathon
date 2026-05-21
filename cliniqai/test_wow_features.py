from fastapi.testclient import TestClient

from agent import server


client = TestClient(server.app)


def reset_in_memory_mode():
    server.MONGODB_URI = ""
    server.patients_collection = None
    server.in_memory_patients.clear()


def sample_payload(phone="9876543210"):
    return {
        "phone": phone,
        "patient_name": "Ramesh Gupta",
        "patient_age": 45,
        "patient_gender": "Male",
        "visit_date": "2026-05-21",
        "doctor_name": "Dr. Sharma",
        "clinic_name": "City Clinic",
        "diagnosis": ["Hypertension"],
        "medicines": [
            {"name": "Aspirin", "dose": "75mg", "frequency": "once daily", "duration": "30 days"},
            {"name": "Atorvastatin", "dose": "10mg", "frequency": "once daily", "duration": "30 days"},
        ],
        "tests_ordered": [],
        "allergies_mentioned": [],
        "notes": "Follow up after 1 month",
        "confidence": {
            "patient_name": 0.95,
            "patient_age": 0.85,
            "patient_gender": 0.90,
            "visit_date": 0.92,
            "doctor_name": 0.60,
            "clinic_name": 0.80,
            "diagnosis": 0.65,
            "medicines": [0.98, 0.55],
            "tests_ordered": 0.90,
            "allergies_mentioned": 0.88,
            "notes": 0.75,
        },
    }


def test_confidence_duplicate_and_audit_features():
    reset_in_memory_mode()

    first = client.post("/test/process", json=sample_payload())
    assert first.status_code == 200
    first_data = first.json()

    assert first_data["duplicate_check"]["is_duplicate"] is False
    assert first_data["confidence"]["needs_review"] is True
    assert "doctor_name" in first_data["confidence"]["low_confidence_fields"]
    assert "diagnosis" in first_data["confidence"]["low_confidence_fields"]
    assert "medicines[1]" in first_data["confidence"]["low_confidence_fields"]

    patient_after_first = client.get("/patient/9876543210").json()["patient"]
    assert len(patient_after_first["visits"]) == 1
    assert len(patient_after_first["audit_log"]) == 1
    assert patient_after_first["audit_log"][0]["action"] == "PATIENT_CREATED"
    assert len(patient_after_first["audit_log"][0]["hash"]) == 64

    second = client.post("/test/process", json=sample_payload())
    assert second.status_code == 200
    second_data = second.json()

    assert second_data["is_returning"] is True
    assert second_data["duplicate_check"]["is_duplicate"] is True
    assert second_data["patient"]["visit_count"] == 1

    patient_after_second = client.get("/patient/9876543210").json()["patient"]
    assert len(patient_after_second["visits"]) == 1
    assert len(patient_after_second["audit_log"]) == 2
    assert patient_after_second["audit_log"][1]["action"] == "DUPLICATE_PRESCRIPTION_BLOCKED"
    assert patient_after_second["audit_log"][1]["previous_hash"] == patient_after_second["audit_log"][0]["hash"]

    changed_payload = sample_payload()
    changed_payload["visit_date"] = "2026-05-22"
    changed_payload["medicines"] = [{"name": "Metformin", "dose": "500mg"}]

    third = client.post("/test/process", json=changed_payload)
    assert third.status_code == 200
    third_data = third.json()

    assert third_data["duplicate_check"]["is_duplicate"] is False
    assert third_data["patient"]["visit_count"] == 2

    patient_after_third = client.get("/patient/9876543210").json()["patient"]
    assert len(patient_after_third["visits"]) == 2
    assert len(patient_after_third["audit_log"]) == 3
    assert patient_after_third["audit_log"][2]["action"] == "VISIT_ADDED"


if __name__ == "__main__":
    test_confidence_duplicate_and_audit_features()
    print("All wow feature tests passed")
