"""Phase 5 Verification Test Suite — QA Mode (Defects, Regression, and Build Acceptance)."""

import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db
from agent.config import AgentConfig
from agent.collectors.qa_collector import QACollector
from agent.normalizer import EventNormalizer
from agent.privacy_filter import PrivacyFilter
from shared.event_types import EventSource, EventType


def test_phase5_qa_mode():
    print("=" * 60)
    print("PROJECTPULSE AI — PHASE 5 QA MODE VERIFICATION")
    print("=" * 60)

    init_db()
    client = TestClient(app)
    config = AgentConfig.load()
    config.role = "QA"
    normalizer = EventNormalizer(config)
    privacy = PrivacyFilter(config)

    # 1. Test QA Collector Event Generation
    print("\n[Step 1] Testing QACollector Event Emitting...")
    events_sent = []

    class MockBackend:
        def send_event(self, event):
            events_sent.append(event)
            r = client.post("/api/events", json=event.model_dump(mode="json"))
            assert r.status_code == 201
            return True

    qa_collector = QACollector(
        config=config,
        normalizer=normalizer,
        privacy_filter=privacy,
        backend=MockBackend(),
    )

    # Defect reporting
    defect_info = qa_collector.report_defect(
        title="Double charge on checkout retry button",
        description="Duplicate payment webhook triggers multiple charges",
        severity="CRITICAL",
        priority="HIGH",
        related_task="PROJ-101",
        reported_by="QA Tester 1",
    )
    assert defect_info["severity"] == "CRITICAL"
    assert len(events_sent) >= 1
    assert events_sent[-1].event_type == EventType.BUG_REPORTED.value
    print(f"  [OK] QACollector reported defect: {defect_info['defect_id']} (BUG_REPORTED emitted)")

    # Defect verification and closing
    qa_collector.verify_defect(defect_info["defect_id"], "Double charge")
    assert events_sent[-1].event_type == EventType.BUG_VERIFIED.value
    print(f"  [OK] QACollector verified defect: {defect_info['defect_id']} (BUG_VERIFIED emitted)")

    qa_collector.close_defect(defect_info["defect_id"], "Double charge")
    assert events_sent[-1].event_type == EventType.BUG_CLOSED.value
    print(f"  [OK] QACollector closed defect: {defect_info['defect_id']} (BUG_CLOSED emitted)")

    # Regression testing events
    qa_collector.start_regression("PaymentSuite-v2")
    assert events_sent[-1].event_type == EventType.REGRESSION_STARTED.value
    print("  [OK] REGRESSION_STARTED event emitted.")

    qa_collector.complete_regression("PaymentSuite-v2", passed_count=24, total_count=25)
    assert events_sent[-1].event_type == EventType.REGRESSION_COMPLETED.value
    print("  [OK] REGRESSION_COMPLETED event emitted.")

    # Build verdict events
    qa_collector.set_build_verdict("Build-RC1", approved=False, reason="Critical payment defect unresolved")
    assert events_sent[-1].event_type == EventType.QA_REJECTED.value
    print("  [OK] QA_REJECTED build verdict emitted.")

    # 2. Test Backend Defect Management APIs
    print("\n[Step 2] Testing Backend Defect Management APIs...")
    defect_payload = {
        "title": "Missing tax calculation on international shipping",
        "description": "Duty taxes are omitted when destination is outside US/EU",
        "severity": "HIGH",
        "priority": "HIGH",
        "related_task_id": "PROJ-104",
        "reported_by": "Liam Johnson",
    }
    res = client.post("/api/projects/DLX/defects", json=defect_payload)
    assert res.status_code == 201, f"Failed to report defect: {res.text}"
    created_def = res.json()
    defect_id = created_def["defect_id"]
    print(f"  [OK] POST /api/projects/DLX/defects -> Created {defect_id} (Status: {created_def['status']})")

    # List defects
    res = client.get("/api/projects/DLX/defects")
    assert res.status_code == 200
    all_defs = res.json()
    assert len(all_defs) >= 1
    print(f"  [OK] GET /api/projects/DLX/defects -> {len(all_defs)} defects in database")

    # Update defect status: OPEN -> VERIFIED -> CLOSED
    res = client.post(f"/api/defects/{defect_id}/status", json={"status": "VERIFIED"})
    assert res.status_code == 200
    assert res.json()["status"] == "VERIFIED"
    print(f"  [OK] Defect {defect_id} status updated to VERIFIED")

    res = client.post(f"/api/defects/{defect_id}/status", json={"status": "CLOSED"})
    assert res.status_code == 200
    assert res.json()["status"] == "CLOSED"
    print(f"  [OK] Defect {defect_id} status updated to CLOSED")

    # 3. Test Build Verdict API
    print("\n[Step 3] Testing QA Build Acceptance Verdict API...")
    verdict_payload = {
        "approved": True,
        "build_ref": "Release-Candidate v1.0",
        "notes": "All critical defects resolved and regression suite verified",
    }
    res = client.post("/api/projects/DLX/qa/verdict", json=verdict_payload)
    assert res.status_code == 200
    print(f"  [OK] POST /api/projects/DLX/qa/verdict -> Verdict: {res.json()['verdict']}")

    # 4. Test QA Metrics & Summary Endpoint
    print("\n[Step 4] Testing GET /api/projects/DLX/qa Endpoint...")
    res = client.get("/api/projects/DLX/qa")
    assert res.status_code == 200
    qa_metrics = res.json()
    print(f"  [OK] Total Defects: {qa_metrics['total_defects']}")
    print(f"  [OK] Open Defects: {qa_metrics['open_defects']}")
    print(f"  [OK] High Severity Defects: {qa_metrics['high_severity_defects']}")
    print(f"  [OK] Closed Defects: {qa_metrics['closed_defects']}")
    print(f"  [OK] Latest QA Build Verdict: {qa_metrics['latest_verdict']}")
    print(f"  [OK] Recent QA Events: {len(qa_metrics['recent_events'])}")

    print("\n" + "=" * 60)
    print(">>> ALL PHASE 5 VERIFICATION TESTS PASSED SUCCESSFULLY! <<<")
    print("=" * 60)


if __name__ == "__main__":
    test_phase5_qa_mode()
