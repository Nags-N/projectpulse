"""Phase 4 Verification Test Suite — Tester Mode (Test Collector, Adapters, and Testing Metrics)."""

import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.main import app
from agent.config import AgentConfig
from agent.collectors.test_collector import JestAdapter, PytestAdapter, TestCollector
from agent.normalizer import EventNormalizer
from agent.privacy_filter import PrivacyFilter
from shared.event_types import EventSource, EventType


def test_phase4_tester_mode():
    print("=" * 60)
    print("PROJECTPULSE AI — PHASE 4 TESTER MODE VERIFICATION")
    print("=" * 60)

    client = TestClient(app)
    config = AgentConfig.load()
    config.role = "TESTER"
    normalizer = EventNormalizer(config)
    privacy = PrivacyFilter(config)

    # 1. Test Pytest Adapter Output Parsing
    print("\n[Step 1] Testing Pytest Output Parsing...")
    pytest_adapter = PytestAdapter()

    # Case A: 18 passed, 2 failed, 1 skipped
    sample_pytest_out = """
    collected 21 items from tests/test_payment.py
    tests/test_payment.py ................. F.F
    =========================== FAILURES ===========================
    FAILED tests/test_payment.py::test_stripe_webhook_timeout
    FAILED tests/test_payment.py::test_idempotent_duplicate_call
    === 2 failed, 18 passed, 1 skipped in 14.25s ===
    """
    res_a = pytest_adapter.parse_output(sample_pytest_out, "", 1, 14.25)
    assert res_a["framework"] == "pytest"
    assert res_a["total"] == 21
    assert res_a["passed"] == 18
    assert res_a["failed"] == 2
    assert res_a["skipped"] == 1
    assert res_a["duration_seconds"] == 14.25
    assert len(res_a["failed_tests"]) == 2
    print(f"  [OK] Pytest adapter parsed: {res_a['passed']} passed, {res_a['failed']} failed, {res_a['skipped']} skipped")

    # Case B: Clean run (all passed)
    clean_out = "=== 25 passed in 3.10s ==="
    res_b = pytest_adapter.parse_output(clean_out, "", 0, 3.10)
    assert res_b["passed"] == 25
    assert res_b["failed"] == 0
    print("  [OK] Pytest clean run parsing verified (100% pass).")

    # 2. Test Jest Adapter Output Parsing
    print("\n[Step 2] Testing Jest Output Parsing...")
    jest_adapter = JestAdapter()
    sample_jest_out = "Tests:  3 failed, 12 passed, 15 total"
    res_jest = jest_adapter.parse_output(sample_jest_out, "", 1, 8.4)
    assert res_jest["framework"] == "jest"
    assert res_jest["passed"] == 12
    assert res_jest["failed"] == 3
    assert res_jest["total"] == 15
    print(f"  [OK] Jest adapter parsed: {res_jest['passed']} passed, {res_jest['failed']} failed")

    # 3. TestCollector Event Ingestion into Backend
    print("\n[Step 3] Testing TestCollector Event Ingestion...")
    events_sent = []

    class MockBackend:
        def send_event(self, event):
            events_sent.append(event)
            r = client.post("/api/events", json=event.model_dump(mode="json"))
            assert r.status_code == 201
            return True

    collector = TestCollector(
        config=config,
        normalizer=normalizer,
        privacy_filter=privacy,
        backend=MockBackend(),
    )

    # Record automated test run outcome
    collector.record_test_run(
        framework="pytest",
        suite_name="AuthSecurityTests",
        total=30,
        passed=28,
        failed=2,
        skipped=0,
        duration_seconds=11.5,
        failed_tests=["test_jwt_expired_refresh", "test_brute_force_lockout"],
    )
    assert len(events_sent) >= 2
    last_event = events_sent[-1]
    assert last_event.source == EventSource.TEST.value
    assert last_event.event_type == EventType.TEST_FAILED.value
    assert last_event.metadata["passed"] == 28
    assert last_event.metadata["failed"] == 2
    print(f"  [OK] TestCollector emitted and persisted: {last_event.title}")

    # 4. Verify Backend Testing Metrics API Endpoint
    print("\n[Step 4] Testing GET /api/projects/DLX/testing Endpoint...")
    res = client.get("/api/projects/DLX/testing")
    assert res.status_code == 200, f"Testing metrics API failed: {res.text}"
    metrics = res.json()
    print(f"  [OK] Total Test Runs in Project: {metrics['total_test_runs']}")
    print(f"  [OK] Total Tests: {metrics['total_tests']}")
    print(f"  [OK] Passed: {metrics['passed']}")
    print(f"  [OK] Failed: {metrics['failed']}")
    print(f"  [OK] Pass Rate: {metrics['pass_rate']}%")
    print(f"  [OK] Recent Test Events Count: {len(metrics['recent_events'])}")
    assert metrics["total_test_runs"] >= 1
    assert metrics["passed"] >= 28

    print("\n" + "=" * 60)
    print(">>> ALL PHASE 4 VERIFICATION TESTS PASSED SUCCESSFULLY! <<<")
    print("=" * 60)


if __name__ == "__main__":
    test_phase4_tester_mode()
