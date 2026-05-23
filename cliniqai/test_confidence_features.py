from fastapi.testclient import TestClient

from agent import server


client = TestClient(server.app)


def reset_in_memory_mode():
    server.MONGODB_URI = ""
    server.patients_collection = None
    server.in_memory_patients.clear()


def payload_with_confidence():
    return {
        "phone": "9998887776",
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


def test_confidence_report_in_test_process():
    reset_in_memory_mode()
    response = client.post("/test/process", json=payload_with_confidence())
    assert response.status_code == 200

    data = response.json()
    assert "confidence" in data
    assert "low_confidence_fields" in data
    assert data["confidence"]["needs_review"] is True
    assert data["confidence"]["threshold"] == 0.7
    assert "doctor_name" in data["confidence"]["low_confidence_fields"]
    assert "medicines[1].name" in data["confidence"]["low_confidence_fields"]
    assert data["patient"]["_confidence"]["name"] == 0.95
    assert data["patient"]["medicines"][0]["_confidence"]["name"] == 0.93
    assert data["patient"]["medicines"][1]["_confidence"]["name"] == 0.45


if __name__ == "__main__":
    test_confidence_report_in_test_process()
    print("Confidence feature test passed")
