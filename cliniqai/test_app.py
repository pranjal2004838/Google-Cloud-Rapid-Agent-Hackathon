"""
CliniqAI — Quick Test Script

Tests the core logic WITHOUT needing API keys:
1. Alert tool (drug conflict checker)
2. Server endpoints (using in-memory store)
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"


def test_health():
    """Test: Health endpoint should return running status."""
    print("\n═══ TEST 1: Health Check ═══")
    r = requests.get(f"{BASE_URL}/health")
    data = r.json()
    print(f"  Status: {data['status']}")
    print(f"  MongoDB: {data['mongodb']}")
    print(f"  Google Cloud Project Set: {data['google_cloud_project_set']}")
    print(f"  GCS Bucket Set: {data['gcs_upload_bucket_set']}")
    assert data["status"] == "running", "FAIL: Server not running"
    print("  ✓ PASSED")


def test_alert_tool_directly():
    """Test: Drug conflict checker should catch penicillin allergy."""
    print("\n═══ TEST 2: Alert Tool (Direct) ═══")
    from agent.tools.alert_tool import check_drug_conflicts

    # Scenario: Patient allergic to penicillin, prescribed amoxicillin
    result = check_drug_conflicts(
        patient_allergies=["penicillin"],
        current_medicines=[{"name": "Metformin"}],
        new_medicines=[{"name": "Amoxicillin"}, {"name": "Paracetamol"}]
    )
    print(f"  Has alerts: {result['has_alerts']}")
    print(f"  Alert count: {result['alert_count']}")
    print(f"  High severity: {result['high_severity']}")
    for alert in result["alerts"]:
        print(f"  → [{alert['severity']}] {alert['message']}")

    assert result["has_alerts"] is True, "FAIL: Should detect allergy conflict"
    assert result["high_severity"] >= 1, "FAIL: Should have at least 1 HIGH alert"
    print("  ✓ PASSED")


def test_alert_no_conflict():
    """Test: No alerts when medicines are safe."""
    print("\n═══ TEST 3: Alert Tool (No Conflict) ═══")
    from agent.tools.alert_tool import check_drug_conflicts

    result = check_drug_conflicts(
        patient_allergies=[],
        current_medicines=[{"name": "Metformin"}],
        new_medicines=[{"name": "Paracetamol"}, {"name": "Vitamin D"}]
    )
    print(f"  Has alerts: {result['has_alerts']}")
    assert result["has_alerts"] is False, "FAIL: Should not have alerts"
    print("  ✓ PASSED")


def test_alert_drug_interaction():
    """Test: Drug-drug interaction detection."""
    print("\n═══ TEST 4: Drug-Drug Interaction ═══")
    from agent.tools.alert_tool import check_drug_conflicts

    # Scenario: Patient on warfarin, new prescription includes aspirin
    result = check_drug_conflicts(
        patient_allergies=[],
        current_medicines=[{"name": "Warfarin"}],
        new_medicines=[{"name": "Aspirin"}, {"name": "Omeprazole"}]
    )
    print(f"  Has alerts: {result['has_alerts']}")
    print(f"  Alert count: {result['alert_count']}")
    for alert in result["alerts"]:
        print(f"  → [{alert['severity']}] {alert['message']}")

    assert result["has_alerts"] is True, "FAIL: Should detect warfarin-aspirin interaction"
    print("  ✓ PASSED")


def test_alert_cross_allergy():
    """Test: Cross-allergy detection (penicillin → cephalosporin)."""
    print("\n═══ TEST 5: Cross-Allergy Detection ═══")
    from agent.tools.alert_tool import check_drug_conflicts

    result = check_drug_conflicts(
        patient_allergies=["penicillin"],
        current_medicines=[],
        new_medicines=[{"name": "Cefixime"}]
    )
    print(f"  Has alerts: {result['has_alerts']}")
    for alert in result["alerts"]:
        print(f"  → [{alert['severity']}] {alert['type']}: {alert['message']}")

    assert result["has_alerts"] is True, "FAIL: Should detect cross-allergy"
    assert any(a["type"] == "CROSS_ALLERGY" for a in result["alerts"]), "FAIL: Should be CROSS_ALLERGY type"
    print("  ✓ PASSED")


def test_query_endpoint():
    """Test: Query endpoint with empty database."""
    print("\n═══ TEST 6: Query Endpoint ═══")
    r = requests.post(f"{BASE_URL}/query", json={"query": "how many patients"})
    data = r.json()
    print(f"  Answer: {data['answer']}")
    assert "0" in data["answer"] or "Total" in data["answer"], "FAIL: Should return count"
    print("  ✓ PASSED")


def test_recent_endpoint():
    """Test: Recent patients endpoint."""
    print("\n═══ TEST 7: Recent Patients ═══")
    r = requests.get(f"{BASE_URL}/recent")
    data = r.json()
    print(f"  Patients returned: {len(data['patients'])}")
    assert "patients" in data, "FAIL: Should return patients key"
    print("  ✓ PASSED")


if __name__ == "__main__":
    print("╔═══════════════════════════════════════╗")
    print("║     CliniqAI Phase 1 Test Suite       ║")
    print("╚═══════════════════════════════════════╝")

    test_health()
    test_alert_tool_directly()
    test_alert_no_conflict()
    test_alert_drug_interaction()
    test_alert_cross_allergy()
    test_query_endpoint()
    test_recent_endpoint()

    print("\n" + "═" * 40)
    print("  ALL TESTS PASSED ✓")
    print("═" * 40)
