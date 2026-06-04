"""
CliniqAI — Multi-Agent Orchestration Tests

Tests the full supervisor pipeline WITHOUT any network calls:
- All extraction is mocked (no Gemini API needed)
- All storage is in-memory (no MongoDB needed)
- All drug checks use rule-based fallback (no API key needed)

Test Coverage:
1. Happy path — new patient, extraction + context + safety + write
2. Allergy alert — penicillin allergy + amoxicillin triggers HIGH alert
3. Returning patient — existing patient updated correctly
4. Duplicate visit detection — same meds within 7 days flagged
5. Low confidence — extraction below threshold triggers review_required
6. Extraction error — workflow fails gracefully, no DB write
7. Trace log — every agent invocation recorded with timing
8. Schema integrity — agents cannot corrupt each other's state slots
9. Agent boundaries — verify each agent only writes its own section
"""

import asyncio
import sys
import os
import time

# Ensure the cliniqai package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.orchestration.supervisor import Supervisor
from agent.orchestration.agents.extraction_agent import ExtractionAgent
from agent.orchestration.agents.patient_context_agent import PatientContextAgent
from agent.orchestration.agents.safety_agent import SafetyAgent
from agent.orchestration.agents.record_update_agent import RecordUpdateAgent
from agent.orchestration.state import WorkflowState, WorkflowStatus
from agent.tools.alert_tool import check_drug_conflicts


# ─── Mock Extraction Functions ────────────────────────────────────────────────

def mock_extraction_healthy(_image_bytes):
    """Simulates a clear prescription with high confidence."""
    return {
        "patient_name": "Ramesh Gupta",
        "patient_age": 45,
        "patient_gender": "Male",
        "visit_date": "2026-05-24",
        "doctor_name": "Dr. Sharma",
        "clinic_name": "City Clinic",
        "diagnosis": ["Type 2 Diabetes", "Hypertension"],
        "medicines": [
            {"name": "Metformin", "dose": "500mg", "frequency": "twice daily", "duration": "30 days"},
            {"name": "Amlodipine", "dose": "5mg", "frequency": "once daily", "duration": "30 days"},
        ],
        "tests_ordered": ["HbA1c", "Lipid Profile"],
        "allergies_mentioned": [],
        "notes": "Follow up in 3 months",
        "confidence": {
            "patient_name": 0.95,
            "patient_age": 0.90,
            "patient_gender": 0.99,
            "visit_date": 0.85,
            "doctor_name": 0.80,
            "clinic_name": 0.75,
            "diagnosis": 0.88,
            "medicines": [
                {"name": 0.92, "dose": 0.88, "frequency": 0.85, "duration": 0.80},
                {"name": 0.95, "dose": 0.90, "frequency": 0.87, "duration": 0.82},
            ],
            "tests_ordered": 0.80,
            "allergies_mentioned": 0.99,
            "notes": 0.70,
        },
    }


def mock_extraction_slow(_image_bytes):
    """Simulates a slow extraction call to verify parallel orchestration."""
    time.sleep(0.2)
    return mock_extraction_healthy(_image_bytes)


def mock_extraction_allergy_conflict(_image_bytes):
    """Simulates prescription with amoxicillin for a penicillin-allergic patient."""
    return {
        "patient_name": "Priya Patel",
        "patient_age": 32,
        "patient_gender": "Female",
        "visit_date": "2026-05-24",
        "doctor_name": "Dr. Verma",
        "clinic_name": "Health Plus",
        "diagnosis": ["Upper Respiratory Infection"],
        "medicines": [
            {"name": "Amoxicillin", "dose": "500mg", "frequency": "thrice daily", "duration": "7 days"},
            {"name": "Paracetamol", "dose": "650mg", "frequency": "as needed", "duration": "5 days"},
        ],
        "tests_ordered": [],
        "allergies_mentioned": ["penicillin"],
        "notes": None,
        "confidence": {
            "patient_name": 0.92,
            "medicines": [{"name": 0.95, "dose": 0.90, "frequency": 0.88, "duration": 0.85}],
        },
    }


def mock_extraction_low_confidence(_image_bytes):
    """Simulates a blurry prescription with low confidence."""
    return {
        "patient_name": "Unknown",
        "patient_age": None,
        "patient_gender": None,
        "visit_date": "2026-05-24",
        "doctor_name": None,
        "clinic_name": None,
        "diagnosis": [],
        "medicines": [
            {"name": "Metformin", "dose": "500mg", "frequency": "once daily", "duration": ""},
        ],
        "tests_ordered": [],
        "allergies_mentioned": [],
        "notes": None,
        "confidence": {
            "patient_name": 0.2,
            "patient_age": 0.1,
            "medicines": [{"name": 0.4, "dose": 0.3, "frequency": 0.3, "duration": 0.1}],
        },
    }


def mock_extraction_error(_image_bytes):
    """Simulates extraction failure."""
    return {"error": "Could not read image file: corrupt data"}


# ─── Helper: Create Supervisor with mocked extraction ─────────────────────────

def create_test_supervisor(extraction_fn, in_memory_store=None):
    """Build a supervisor with mock extraction and in-memory storage."""
    if in_memory_store is None:
        in_memory_store = []

    return Supervisor(
        extraction_agent=ExtractionAgent(extraction_fn=extraction_fn),
        patient_context_agent=PatientContextAgent(
            db_collection=None,
            in_memory_store=in_memory_store,
        ),
        safety_agent=SafetyAgent(check_fn=check_drug_conflicts),
        record_update_agent=RecordUpdateAgent(
            db_collection=None,
            in_memory_store=in_memory_store,
        ),
    )


# ─── Test 1: Happy Path — New Patient ────────────────────────────────────────

async def test_happy_path_new_patient():
    """New patient: extraction + context + safety + write — all succeed."""
    store = []
    supervisor = create_test_supervisor(mock_extraction_healthy, store)

    state = await supervisor.run(
        phone="9876543210",
        image_bytes=b"fake_image_data",
        ip_address="127.0.0.1",
    )

    # Workflow should complete
    assert state.status == WorkflowStatus.COMPLETED, f"Expected COMPLETED, got {state.status}"

    # Extraction should populate
    assert state.extracted_data is not None
    assert state.extracted_data.patient_name == "Ramesh Gupta"
    assert len(state.extracted_data.medicines) == 2

    # Patient context: new patient
    assert state.patient_context is not None
    assert state.patient_context.patient_exists is False

    # Safety: no allergies, no conflicts
    assert state.safety_assessment is not None
    assert state.safety_assessment.has_alerts is False

    # Write: record created
    assert state.write_result is not None
    assert state.write_result.record_id != ""
    assert state.write_result.is_returning is False
    assert state.write_result.visit_count == 1
    assert state.write_result.audit_chain_valid is True

    # Trace: should have entries for all 4 agents
    agent_names = [t.agent for t in state.trace]
    assert "ExtractionAgent" in agent_names
    assert "PatientContextAgent" in agent_names
    assert "SafetyAgent" in agent_names
    assert "RecordUpdateAgent" in agent_names

    # In-memory store should have 1 patient
    assert len(store) == 1
    assert store[0]["phone"] == "9876543210"
    assert store[0]["name"] == "[ENCRYPTED_KMS]"
    
    # Verify KMS decryption
    from agent.gcp.kms import decrypt_data
    decrypted = decrypt_data(store[0]["secure_pii"])
    assert decrypted["name"] == "Ramesh Gupta"
    assert decrypted["age"] == 45
    assert decrypted["gender"] == "Male"

    print("  PASS: test_happy_path_new_patient")


# ─── Test 2: Allergy Alert — HIGH severity ───────────────────────────────────

async def test_allergy_alert():
    """Patient with penicillin allergy prescribed amoxicillin → HIGH alert."""
    store = []
    supervisor = create_test_supervisor(mock_extraction_allergy_conflict, store)

    state = await supervisor.run(
        phone="9998887770",
        image_bytes=b"fake_image_data",
        ip_address="127.0.0.1",
    )

    # Should be review_required due to HIGH alert
    assert state.status == WorkflowStatus.REVIEW_REQUIRED, f"Expected REVIEW_REQUIRED, got {state.status}"
    assert "HIGH" in (state.review_reason or "")

    # Safety should have HIGH alert
    assert state.safety_assessment is not None
    assert state.safety_assessment.has_alerts is True
    assert state.safety_assessment.high_severity_count >= 1
    assert state.safety_assessment.requires_override is True

    # Check alert content
    alert_messages = [a.message for a in state.safety_assessment.alerts]
    assert any("penicillin" in m.lower() or "allergy" in m.lower() for m in alert_messages)

    # Record should still be written (flagged, not blocked)
    assert state.write_result is not None
    assert state.write_result.record_id != ""

    print("  PASS: test_allergy_alert")


# ─── Test 3: Returning Patient ────────────────────────────────────────────────

async def test_returning_patient():
    """Second visit for same phone → patient updated, not duplicated."""
    store = []
    supervisor = create_test_supervisor(mock_extraction_healthy, store)

    # First visit
    state1 = await supervisor.run(
        phone="1112223330",
        image_bytes=b"first_visit",
        ip_address="127.0.0.1",
    )
    assert state1.status == WorkflowStatus.COMPLETED
    assert len(store) == 1

    # Second visit (same phone, same supervisor with same store)
    supervisor2 = create_test_supervisor(mock_extraction_healthy, store)
    state2 = await supervisor2.run(
        phone="1112223330",
        image_bytes=b"second_visit",
        ip_address="127.0.0.1",
    )

    # Should still be 1 patient in store (updated, not duplicated)
    assert len(store) == 1, f"Expected 1 patient, got {len(store)}"
    assert state2.write_result is not None
    assert state2.write_result.is_returning is True
    assert state2.write_result.visit_count == 2

    # Patient context should detect existing patient
    assert state2.patient_context is not None
    assert state2.patient_context.patient_exists is True

    print("  PASS: test_returning_patient")


# ─── Test 4: Duplicate Visit Detection ───────────────────────────────────────

async def test_duplicate_visit():
    """Same meds uploaded twice within minutes → duplicate flagged."""
    store = []
    supervisor = create_test_supervisor(mock_extraction_healthy, store)

    # First upload
    await supervisor.run(phone="5554443330", image_bytes=b"img1", ip_address="127.0.0.1")

    # Immediate second upload (same meds)
    supervisor2 = create_test_supervisor(mock_extraction_healthy, store)
    state2 = await supervisor2.run(phone="5554443330", image_bytes=b"img2", ip_address="127.0.0.1")

    # Patient context should detect duplicate
    assert state2.patient_context is not None
    dup = state2.patient_context.duplicate_check
    assert dup.get("is_duplicate") is True, f"Expected duplicate, got {dup}"
    assert "similarity" in dup

    print("  PASS: test_duplicate_visit")


# ─── Test 5: Low Confidence → Review Required ────────────────────────────────

async def test_low_confidence_review():
    """Blurry prescription with low confidence → review_required."""
    store = []
    supervisor = create_test_supervisor(mock_extraction_low_confidence, store)

    state = await supervisor.run(
        phone="7776665550",
        image_bytes=b"blurry_image",
        ip_address="127.0.0.1",
    )

    assert state.status == WorkflowStatus.REVIEW_REQUIRED
    assert "confidence" in (state.review_reason or "").lower()

    # Should still write the record (flagged for review, not blocked)
    assert state.write_result is not None
    assert state.write_result.record_id != ""

    print("  PASS: test_low_confidence_review")


# ─── Test 6: Extraction Error → Workflow Fails Gracefully ─────────────────────

async def test_extraction_error():
    """Corrupt image → workflow fails, no DB write."""
    store = []
    supervisor = create_test_supervisor(mock_extraction_error, store)

    state = await supervisor.run(
        phone="0001112220",
        image_bytes=b"corrupt_data",
        ip_address="127.0.0.1",
    )

    assert state.status == WorkflowStatus.FAILED
    assert state.error is not None
    assert "failed" in state.error.lower() or "error" in state.error.lower()

    # No patient should be written
    assert len(store) == 0

    print("  PASS: test_extraction_error")


# ─── Test 7: Trace Log Completeness ──────────────────────────────────────────

async def test_trace_log():
    """Every agent invocation should appear in the trace with timing."""
    store = []
    supervisor = create_test_supervisor(mock_extraction_healthy, store)

    state = await supervisor.run(
        phone="3332221110",
        image_bytes=b"img",
        ip_address="127.0.0.1",
    )

    # Should have at least 4 trace entries (one per agent)
    assert len(state.trace) >= 4, f"Expected >=4 trace entries, got {len(state.trace)}"

    for entry in state.trace:
        assert entry.agent != ""
        assert entry.started_at != ""
        assert entry.finished_at != ""
        assert entry.duration_ms >= 0
        assert entry.status in ("success", "failed", "skipped")

    # All should be success in happy path
    assert all(t.status == "success" for t in state.trace)

    print("  PASS: test_trace_log")


# ─── Test 8: Schema Integrity ────────────────────────────────────────────────

async def test_schema_integrity():
    """Verify Pydantic models enforce correct types."""
    store = []
    supervisor = create_test_supervisor(mock_extraction_healthy, store)

    state = await supervisor.run(
        phone="4445556660",
        image_bytes=b"img",
        ip_address="127.0.0.1",
    )

    # Verify all state sections are proper Pydantic models
    from agent.orchestration.state import (
        ExtractedData, PatientContext, SafetyAssessment, WriteResult
    )
    assert isinstance(state.extracted_data, ExtractedData)
    assert isinstance(state.patient_context, PatientContext)
    assert isinstance(state.safety_assessment, SafetyAssessment)
    assert isinstance(state.write_result, WriteResult)

    # Medicines should be canonical Medicine objects
    for med in state.extracted_data.medicines:
        assert hasattr(med, "name")
        assert hasattr(med, "dose")
        assert hasattr(med, "frequency")

    print("  PASS: test_schema_integrity")


# ─── Test 9: Agent Boundaries (Isolation) ────────────────────────────────────

async def test_agent_boundaries():
    """
    Verify each agent only writes to its own section.
    After extraction, patient_context should still be None.
    After context, safety_assessment should still be None.
    """
    store = []

    # We test this by running a supervisor and checking intermediate states
    # aren't corrupted. The best we can do without intercepting is check
    # that the final state has each section written by exactly the right agent.
    supervisor = create_test_supervisor(mock_extraction_healthy, store)
    state = await supervisor.run(
        phone="8889990000",
        image_bytes=b"img",
        ip_address="127.0.0.1",
    )

    # ExtractionAgent output should not contain DB-related fields
    assert not hasattr(state.extracted_data, "record_id")
    assert not hasattr(state.extracted_data, "patient_exists")

    # PatientContext should not contain medicines from extraction
    # (it has current_medicines from PRIOR visits, which should be empty for new patient)
    assert len(state.patient_context.current_medicines) == 0

    # SafetyAssessment should not contain write results
    assert not hasattr(state.safety_assessment, "record_id")

    # WriteResult should not contain alert data
    assert not hasattr(state.write_result, "alerts")

    print("  PASS: test_agent_boundaries")


# ─── Test 10: extracted_override (test/process path) ─────────────────────────

async def test_extracted_override():
    """Supervisor with extracted_override should skip real extraction."""
    store = []
    supervisor = create_test_supervisor(mock_extraction_error, store)  # would fail if called

    # Using extracted_override should bypass the broken extraction_fn
    state = await supervisor.run(
        phone="6667778880",
        ip_address="test-client",
        extracted_override={
            "patient_name": "Override Patient",
            "patient_age": 30,
            "patient_gender": "Female",
            "visit_date": "2026-05-24",
            "doctor_name": "Dr. Test",
            "diagnosis": ["Fever"],
            "medicines": [{"name": "Paracetamol", "dose": "500mg", "frequency": "thrice daily", "duration": "3 days"}],
            "tests_ordered": [],
            "allergies_mentioned": [],
            "confidence": {"patient_name": 0.99, "medicines": [{"name": 0.99}]},
        },
    )

    assert state.status == WorkflowStatus.COMPLETED, f"Expected COMPLETED, got {state.status}; error={state.error}"
    assert state.extracted_data.patient_name == "Override Patient"
    assert len(store) == 1
    assert store[0]["name"] == "[ENCRYPTED_KMS]"
    
    # Verify KMS decryption
    from agent.gcp.kms import decrypt_data
    decrypted = decrypt_data(store[0]["secure_pii"])
    assert decrypted["name"] == "Override Patient"
    assert decrypted["age"] == 30
    assert decrypted["gender"] == "Female"

    print("  PASS: test_extracted_override")


# ─── Test 11: Parallel Execution (Extraction + Context) ─────────────────────

async def test_parallel_execution():
    """Context lookup should complete before slow extraction (parallel startup)."""
    store = []
    supervisor = create_test_supervisor(mock_extraction_slow, store)

    state = await supervisor.run(
        phone="1212121212",
        image_bytes=b"img",
        ip_address="127.0.0.1",
    )

    assert state.status in (WorkflowStatus.COMPLETED, WorkflowStatus.REVIEW_REQUIRED)

    # Expect at least two PatientContext entries (parallel lookup + post-extraction merge)
    context_entries = [t for t in state.trace if t.agent == "PatientContextAgent"]
    assert len(context_entries) >= 2, f"Expected >=2 PatientContext traces, got {len(context_entries)}"

    extraction_entries = [t for t in state.trace if t.agent == "ExtractionAgent"]
    assert extraction_entries, "Missing ExtractionAgent trace"

    # The first context run should be fast; extraction should be slower due to sleep.
    assert extraction_entries[0].duration_ms >= context_entries[0].duration_ms

    print("  PASS: test_parallel_execution")


# ─── Run All Tests ────────────────────────────────────────────────────────────

async def run_all_tests():
    print("\n" + "=" * 60)
    print("CliniqAI Multi-Agent Orchestration Tests")
    print("=" * 60 + "\n")

    tests = [
        test_happy_path_new_patient,
        test_allergy_alert,
        test_returning_patient,
        test_duplicate_visit,
        test_low_confidence_review,
        test_extraction_error,
        test_trace_log,
        test_schema_integrity,
        test_agent_boundaries,
        test_extracted_override,
        test_parallel_execution,
    ]

    passed = 0
    failed = 0

    import traceback
    for test_fn in tests:
        try:
            await test_fn()
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {test_fn.__name__}: {e}")
            traceback.print_exc()
            failed += 1
        except Exception as e:
            print(f"  ERROR: {test_fn.__name__} ({type(e).__name__}): {e}")
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    print("=" * 60 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
