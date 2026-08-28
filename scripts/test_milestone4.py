"""End-to-end test for Milestone 4 frontend integration."""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.config import AgentConfig

BASE = "http://127.0.0.1:8000"
config = AgentConfig.load()


def register_agent_entities(client: httpx.Client) -> None:
    """Ensure agent config user/project exist in the backend."""
    try:
        client.post(
            f"{BASE}/api/users",
            json={
                "user_id": config.user_id,
                "name": config.user_name,
                "role": "DEVELOPER",
            },
        )
    except httpx.HTTPError:
        pass

    try:
        client.post(
            f"{BASE}/api/projects",
            json={
                "project_id": config.project_id,
                "name": config.project_name,
                "folder_path": config.project_folder,
                "owner_user_id": config.user_id,
            },
        )
    except httpx.HTTPError:
        pass


def main() -> int:
    print("ProjectPulse Milestone 4 E2E Test")
    print(f"  project_id: {config.project_id}")
    print(f"  user_id:    {config.user_id}")

    with httpx.Client(timeout=10.0) as client:
        health = client.get(f"{BASE}/api/health")
        health.raise_for_status()
        print("[OK] Backend health OK")

        register_agent_entities(client)

        # Simulate file modification event (same shape as file watcher)
        test_file = ROOT / "frontend_e2e_test.txt"
        test_file.write_text(f"e2e test {datetime.now().isoformat()}\n", encoding="utf-8")

        event_payload = {
            "project_id": config.project_id,
            "user_id": config.user_id,
            "role": "DEVELOPER",
            "source": "VS_CODE",
            "event_type": "FILE_MODIFIED",
            "title": f"Modified {test_file.name}",
            "description": "Milestone 4 E2E test event",
            "status": "INFO",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {"file": str(test_file.relative_to(ROOT)).replace("\\", "/")},
        }
        resp = client.post(f"{BASE}/api/events", json=event_payload)
        resp.raise_for_status()
        print("[OK] FILE_MODIFIED event ingested")

        summary = client.get(
            f"{BASE}/api/projects/{config.project_id}/summary",
            params={"user_id": config.user_id},
        )
        summary.raise_for_status()
        dev = summary.json()
        assert dev["project_name"], "Missing project name in developer summary"
        assert dev["activity"]["file_modifications"] >= 1, "File modification not in developer summary"
        print(f"[OK] Developer summary: {dev['activity']['file_modifications']} file modification(s)")

        dashboard = client.get(
            f"{BASE}/api/projects/{config.project_id}/dashboard",
            params={"role": "PROJECT_MANAGER"},
        )
        dashboard.raise_for_status()
        mgr = dashboard.json()
        assert mgr["activity"]["file_modifications"] >= 1, "File modification not in manager dashboard"
        print(f"[OK] Manager dashboard: {mgr['activity']['file_modifications']} file modification(s)")

        # Test frontend proxy path
        try:
            fe = httpx.get("http://127.0.0.1:5173/api/config", timeout=5.0)
            if fe.status_code == 200:
                print("[OK] Frontend proxy to /api/config OK")
            else:
                print(f"[WARN] Frontend proxy returned {fe.status_code}")
        except httpx.HTTPError as exc:
            print(f"[WARN] Frontend not reachable: {exc}")

        print("\nAll API checks passed.")
        print(f"Developer UI: {config.frontend_url}/developer?project_id={config.project_id}&user_id={config.user_id}")
        print(f"Manager UI:   {config.frontend_url}/manager?project_id={config.project_id}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
