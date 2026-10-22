"""Phase 6 & 7 Verification Test Suite — Multi-Agent Fleet & PM Master Dashboard."""

import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db


def test_phase7_pm_dashboard():
    print("=" * 60)
    print("PROJECTPULSE AI — PHASE 6 & 7 PM MASTER DASHBOARD TEST")
    print("=" * 60)

    init_db()
    client = TestClient(app)

    # 1. Query Manager Dashboard
    print("\n[Step 1] Querying GET /api/projects/DLX/dashboard...")
    res = client.get("/api/projects/DLX/dashboard")
    assert res.status_code == 200, f"Dashboard fetch failed: {res.text}"
    dash = res.json()

    # 2. Verify Health Scorecard
    print("\n[Step 2] Verifying Explainable Health Scorecard...")
    health = dash["health"]
    print(f"  [OK] Overall Health Status: {health['overall_status']}")
    print(f"  [OK] Tasks Planned: {health['tasks_status']}")
    print(f"  [OK] Development Status: {health['development_status']}")
    print(f"  [OK] Testing Status: {health['testing_status']}")
    print(f"  [OK] QA Defects: {health['qa_status']}")
    print(f"  [OK] Dependencies: {health['dependencies_status']}")
    assert "overall_status" in health

    # 3. Verify Team Agent Fleet
    print("\n[Step 3] Verifying Multi-Agent Connected Fleet...")
    agents = dash["team_agents"]
    print(f"  [OK] Total Connected Agents: {len(agents)}")
    roles = {a["role"] for a in agents}
    assert "DEVELOPER" in roles, "Expected DEVELOPER agents"
    assert "TESTER" in roles, "Expected TESTER agents"
    assert "QA" in roles, "Expected QA agents"
    for a in agents[:4]:
        print(f"    - {a['agent_id']} ({a['role']}) on {a['machine_name']} [{a['status']}]")

    # 4. Verify Tasks Summary (Planned vs Actual)
    print("\n[Step 4] Verifying Planned Tasks Summary...")
    tasks = dash["tasks_summary"]
    print(f"  [OK] Total Tasks: {tasks['total']}")
    print(f"  [OK] Completed: {tasks['completed']}")
    print(f"  [OK] In Progress: {tasks['in_progress']}")
    print(f"  [OK] Blocked: {tasks['blocked']}")
    assert tasks["total"] >= 4

    # 5. Verify Unified Timeline Events
    print("\n[Step 5] Verifying Unified Cross-Role Timeline...")
    events = dash["recent_events"]
    print(f"  [OK] Recent Unified Events Count: {len(events)}")
    sources = {e["source"] for e in events}
    print(f"  [OK] Event Sources detected in timeline: {sources}")
    assert len(events) > 0

    print("\n" + "=" * 60)
    print(">>> ALL PHASE 6 & 7 VERIFICATION TESTS PASSED SUCCESSFULLY! <<<")
    print("=" * 60)


if __name__ == "__main__":
    test_phase7_pm_dashboard()
