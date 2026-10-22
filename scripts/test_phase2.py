"""Phase 2 Verification Test Suite — Multi-Role Agent Registration & Simulation."""

import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.main import app
from agent.config import AgentConfig
from agent.setup_wizard import run_setup


def test_phase2_agent_registration():
    print("=" * 60)
    print("PROJECTPULSE AI — PHASE 2 AGENT REGISTRATION & SETUP TEST")
    print("=" * 60)

    client = TestClient(app)

    # 1. Test Setup Wizard for Developer Role
    print("\n[Step 1] Testing Setup Wizard for DEVELOPER role...")
    dev_cfg_path = ROOT / "agent" / "config" / "test_agent_dev.json"
    cfg_dev = run_setup([
        "--role", "DEVELOPER",
        "--agent-id", "TEST-AGENT-DEV-001",
        "--user-id", "DEV-001",
        "--user-name", "Test Developer",
        "--project-id", "DLX",
        "--output-config", str(dev_cfg_path),
        "--non-interactive"
    ])
    assert cfg_dev.role == "DEVELOPER"
    assert cfg_dev.agent_id == "TEST-AGENT-DEV-001"
    print("  [OK] Developer Agent config generated and loaded.")

    # 2. Test Setup Wizard for Tester Role
    print("\n[Step 2] Testing Setup Wizard for TESTER role...")
    tester_cfg_path = ROOT / "agent" / "config" / "test_agent_tester.json"
    cfg_test = run_setup([
        "--role", "TESTER",
        "--agent-id", "TEST-AGENT-TEST-001",
        "--user-id", "TEST-001",
        "--user-name", "Test QA Engineer",
        "--project-id", "DLX",
        "--output-config", str(tester_cfg_path),
        "--non-interactive"
    ])
    assert cfg_test.role == "TESTER"
    assert cfg_test.agent_id == "TEST-AGENT-TEST-001"
    print("  [OK] Tester Agent config generated and loaded.")

    # 3. Test Setup Wizard for QA Role
    print("\n[Step 3] Testing Setup Wizard for QA role...")
    qa_cfg_path = ROOT / "agent" / "config" / "test_agent_qa.json"
    cfg_qa = run_setup([
        "--role", "QA",
        "--agent-id", "TEST-AGENT-QA-001",
        "--user-id", "QA-001",
        "--user-name", "Lead QA Specialist",
        "--project-id", "DLX",
        "--output-config", str(qa_cfg_path),
        "--non-interactive"
    ])
    assert cfg_qa.role == "QA"
    assert cfg_qa.agent_id == "TEST-AGENT-QA-001"
    print("  [OK] QA Agent config generated and loaded.")

    # 4. Verify API Registration for all roles
    print("\n[Step 4] Verifying agent registration via backend API...")
    for cfg in [cfg_dev, cfg_test, cfg_qa]:
        res = client.post("/api/agents/register", json={
            "agent_id": cfg.agent_id,
            "user_id": cfg.user_id,
            "project_id": cfg.project_id,
            "role": cfg.role,
            "machine_name": cfg.machine_name,
            "machine_id": cfg.machine_id,
        })
        assert res.status_code in (200, 201), f"Registration failed: {res.text}"
        print(f"  [OK] Agent {cfg.agent_id} verified in backend (Role: {cfg.role})")

    # 5. Verify Heartbeats
    print("\n[Step 5] Verifying Agent Heartbeats...")
    for cfg in [cfg_dev, cfg_test, cfg_qa]:
        hb_res = client.post("/api/agents/heartbeat", json={
            "agent_id": cfg.agent_id,
            "monitoring_active": True,
        })
        assert hb_res.status_code == 200
        assert hb_res.json()["agent_status"] == "ONLINE"
        print(f"  [OK] Heartbeat confirmed for {cfg.agent_id} -> ONLINE")

    # 6. Verify Multi-Agent Query
    print("\n[Step 6] Listing all agents from backend...")
    res = client.get("/api/agents?project_id=DLX")
    assert res.status_code == 200
    agents = res.json()
    agent_ids = [a["agent_id"] for a in agents]
    assert "TEST-AGENT-DEV-001" in agent_ids
    assert "TEST-AGENT-TEST-001" in agent_ids
    assert "TEST-AGENT-QA-001" in agent_ids
    print(f"  [OK] Total agents connected: {len(agents)}")
    for a in agents[:5]:
        print(f"    - {a['agent_id']} [{a['role']}] on {a['machine_name']} ({a['status']})")

    # Clean up test configs
    for p in [dev_cfg_path, tester_cfg_path, qa_cfg_path]:
        if p.exists():
            p.unlink()

    print("\n" + "=" * 60)
    print(">>> ALL PHASE 2 VERIFICATION TESTS PASSED SUCCESSFULLY! <<<")
    print("=" * 60)


if __name__ == "__main__":
    test_phase2_agent_registration()
