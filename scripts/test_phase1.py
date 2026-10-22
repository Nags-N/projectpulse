"""Phase 1 Verification Test Suite for ProjectPulse AI."""

import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal, init_db
from backend.models.db_models import Agent, Project, ProjectEventRecord, TaskRecord, User
from backend.services.seed_service import seed_demo_data
from shared.event_types import EventSource, EventType, UserRole


def test_phase1_foundation():
    print("=" * 60)
    print("PROJECTPULSE AI — PHASE 1 FOUNDATION TEST SUITE")
    print("=" * 60)

    # 1. Initialize Database & Seed
    print("\n[Step 1] Initializing SQLite database...")
    init_db()
    db = SessionLocal()
    try:
        seed_demo_data(db)
        user_count = db.query(User).count()
        project_count = db.query(Project).count()
        agent_count = db.query(Agent).count()
        task_count = db.query(TaskRecord).count()
        event_count = db.query(ProjectEventRecord).count()

        print(f"  [OK] Users in DB: {user_count}")
        print(f"  [OK] Projects in DB: {project_count}")
        print(f"  [OK] Agents in DB: {agent_count}")
        print(f"  [OK] Tasks in DB: {task_count}")
        print(f"  [OK] Events in DB: {event_count}")
        assert user_count >= 6, "Expected at least 6 seeded users"
        assert project_count >= 1, "Expected at breath at least 1 seeded project"
        assert agent_count >= 6, "Expected at least 6 multi-role agents"
        assert task_count >= 4, "Expected at least 4 normalized tasks"
        print("  [OK] Database models and seeding verified!")
    finally:
        db.close()

    # 2. Test FastAPI Endpoints via TestClient
    print("\n[Step 2] Testing FastAPI backend endpoints...")
    client = TestClient(app)

    # Health check
    res = client.get("/api/health")
    assert res.status_code == 200, f"Health check failed: {res.status_code}"
    print(f"  [OK] GET /api/health -> {res.json()}")

    # App Config
    res = client.get("/api/config")
    assert res.status_code == 200
    print(f"  [OK] GET /api/config -> project_id: {res.json()['project_id']}")

    # 3. Agent Registration & Heartbeat
    print("\n[Step 3] Testing Agent registration & heartbeat...")
    new_agent_payload = {
        "agent_id": "AGENT-TESTER-099",
        "user_id": "TEST-001",
        "project_id": "DLX",
        "role": "TESTER",
        "machine_name": "QA-AUTOMATION-RIG",
        "machine_id": "RIG-UUID-99",
    }
    res = client.post("/api/agents/register", json=new_agent_payload)
    assert res.status_code == 201, f"Agent registration failed: {res.text}"
    agent_data = res.json()
    print(f"  [OK] POST /api/agents/register -> Registered {agent_data['agent_id']} ({agent_data['role']})")

    # Agent Heartbeat
    hb_payload = {"agent_id": "AGENT-TESTER-099", "monitoring_active": True}
    res = client.post("/api/agents/heartbeat", json=hb_payload)
    assert res.status_code == 200
    print(f"  [OK] POST /api/agents/heartbeat -> {res.json()}")

    # List Agents
    res = client.get("/api/agents?project_id=DLX")
    assert res.status_code == 200
    agents = res.json()
    print(f"  [OK] GET /api/agents -> {len(agents)} active agents registered")

    # 4. Ingest Events Across Roles
    print("\n[Step 4] Testing Normalized Event Ingestion (Dev, Tester, QA)...")
    # Developer Git Commit Event
    dev_event = {
        "agent_id": "AGENT-DEV-001",
        "user_id": "DEV-001",
        "project_id": "DLX",
        "role": "DEVELOPER",
        "source": "GIT",
        "event_type": "GIT_COMMIT",
        "title": "Commit 4b912a: Fix payment timeout validation",
        "description": "Added exponential backoff to Stripe charges",
        "status": "INFO",
        "metadata": {"branch": "feature/payment", "commit_hash": "4b912a"},
    }
    res = client.post("/api/events", json=dev_event)
    assert res.status_code == 201
    print(f"  [OK] Developer event ingested: {res.json()['event_id']}")

    # Tester Pytest Failure Event
    tester_event = {
        "agent_id": "AGENT-TESTER-099",
        "user_id": "TEST-001",
        "project_id": "DLX",
        "role": "TESTER",
        "source": "TEST",
        "event_type": "TEST_FAILED",
        "title": "pytest test_payment_gateway.py: 3 failed",
        "description": "AssertionError: 504 Gateway Timeout not handled",
        "status": "WARNING",
        "metadata": {"framework": "pytest", "failed": 3, "passed": 12, "suite": "PaymentTests"},
    }
    res = client.post("/api/events", json=tester_event)
    assert res.status_code == 201
    print(f"  [OK] Tester event ingested: {res.json()['event_id']}")

    # QA Bug Reported Event
    qa_event = {
        "agent_id": "AGENT-QA-001",
        "user_id": "QA-001",
        "project_id": "DLX",
        "role": "QA",
        "source": "QA",
        "event_type": "BUG_REPORTED",
        "title": "HIGH Severity: Double charge occurs when user double-clicks Pay",
        "description": "Checkout screen allows multiple clicks before disabling the button",
        "status": "ERROR",
        "metadata": {"severity": "HIGH", "module": "Checkout"},
    }
    res = client.post("/api/events", json=qa_event)
    assert res.status_code == 201
    print(f"  [OK] QA event ingested: {res.json()['event_id']}")

    # Query Events by Role
    res = client.get("/api/events?project_id=DLX&role=TESTER")
    assert res.status_code == 200
    tester_events = res.json()
    print(f"  [OK] Filtered GET /api/events?role=TESTER -> {len(tester_events)} events")

    # 5. Test Manager Dashboard & Developer Summary
    print("\n[Step 5] Testing Manager Dashboard and Developer Summary...")
    res = client.get("/api/projects/DLX/dashboard")
    assert res.status_code == 200
    dash = res.json()
    print(f"  [OK] Manager Dashboard Signals: {dash['signals']}")
    print(f"  [OK] Total Activities: {dash['activity']['total_activities']}")
    print(f"  [OK] Test Failures: {dash['activity']['test_failures']}")
    print(f"  [OK] Bugs Reported: {dash['activity']['bugs_reported']}")

    res = client.get("/api/projects/DLX/summary?user_id=DEV-001")
    assert res.status_code == 200
    dev_sum = res.json()
    print(f"  [OK] Developer Summary Status: {dev_sum['current_status']}")

    # 6. Test Tasks API
    print("\n[Step 6] Testing Normalized Tasks API...")
    res = client.get("/api/tasks?project_id=DLX")
    assert res.status_code == 200
    tasks = res.json()
    print(f"  [OK] Tasks retrieved: {len(tasks)}")
    for t in tasks:
        print(f"    - [{t['source']}] {t['external_task_id']}: {t['title']} ({t['status']})")

    print("\n" + "=" * 60)
    print(">>> ALL PHASE 1 VERIFICATION TESTS PASSED SUCCESSFULLY! <<<")
    print("=" * 60)


if __name__ == "__main__":
    test_phase1_foundation()
