from fastapi.testclient import TestClient

from agent import server


client = TestClient(server.app)


def reset_in_memory_mode():
    server.MONGODB_URI = ""
    server.patients_collection = None
    server.in_memory_patients.clear()


def _payload(phone: str = "9991112223"):
    return {
        "phone": phone,
        "patient_name": "Ramesh Gupta",
        "patient_age": 45,
        "patient_gender": "Male",
        "visit_date": "2026-05-22",
        "doctor_name": "Dr. Sharma",
        "clinic_name": "City Clinic",
        "diagnosis": ["Hypertension"],
        "medicines": [
            {"name": "Metformin", "dose": "500mg", "frequency": "twice daily", "duration": "30 days"},
            {"name": "Amlodipine", "dose": "5mg", "frequency": "once daily", "duration": "30 days"},
        ],
        "tests_ordered": [],
        "allergies_mentioned": [],
        "notes": "Follow up after 1 month",
        "confidence": {
            "patient_name": 0.95,
            "patient_age": 0.88,
            "patient_gender": 0.92,
            "visit_date": 0.9,
            "doctor_name": 0.68,
            "clinic_name": 0.9,
            "diagnosis": 0.82,
            "medicines": [
                {"name": 0.93, "dose": 0.94, "frequency": 0.9, "duration": 0.9},
                {"name": 0.45, "dose": 0.9, "frequency": 0.88, "duration": 0.9},
            ],
            "tests_ordered": 0.9,
            "allergies_mentioned": 0.9,
            "notes": 0.88,
        },
    }


def test_duplicate_prevention_and_audit_chain():
    reset_in_memory_mode()
    first = client.post("/test/process", json=_payload())
    assert first.status_code == 200
    first_data = first.json()
    assert first_data["duplicate_check"]["is_duplicate"] is False
    assert first_data["audit"]["entries"] == 1
    assert first_data["audit"]["chain_valid"] is True

    second = client.post("/test/process", json=_payload())
    assert second.status_code == 200
    second_data = second.json()
    assert second_data["is_returning"] is True
    assert second_data["duplicate_check"]["is_duplicate"] is True
    assert second_data["duplicate_check"]["similarity"] >= 0.95
    assert second_data["audit"]["entries"] == 2
    assert second_data["audit"]["chain_valid"] is True


def test_alert_acknowledge_creates_immutable_event():
    reset_in_memory_mode()
    seed = client.post("/test/process", json=_payload(phone="8887776665"))
    assert seed.status_code == 200

    ack = client.post(
        "/alerts/acknowledge",
        json={
            "phone": "8887776665",
            "doctor_name": "Dr. Sharma",
            "alert": "WARFARIN + ASPIRIN",
            "override_reason": "Patient stopped aspirin 2 days ago",
        },
    )
    assert ack.status_code == 200
    ack_data = ack.json()
    assert ack_data["ok"] is True
    assert ack_data["event"]["action"] == "ALERT_ACKNOWLEDGED"
    assert ack_data["event"]["details"]["override_reason"] == "Patient stopped aspirin 2 days ago"
    assert ack_data["chain_valid"] is True
    assert ack_data["audit_entries"] == 2


if __name__ == "__main__":
    test_duplicate_prevention_and_audit_chain()
    test_alert_acknowledge_creates_immutable_event()
    print("Wow feature tests passed")
