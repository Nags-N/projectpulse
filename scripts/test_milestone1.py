"""Milestone 1 smoke test — run after starting the backend."""

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httpx

BASE = "http://127.0.0.1:8000"


def main():
    print("ProjectPulse AI — Milestone 1 Smoke Test")
    print("=" * 40)

    # Health
    r = httpx.get(f"{BASE}/api/health", timeout=5)
    assert r.status_code == 200, f"Health check failed: {r.text}"
    print("[OK] Health check")

    # Register user
    r = httpx.post(
        f"{BASE}/api/users",
        json={"name": "Test Developer", "role": "DEVELOPER"},
        timeout=5,
    )
    assert r.status_code == 201, f"User registration failed: {r.text}"
    user_id = r.json()["user_id"]
    print(f"[OK] User registered: {user_id}")

    # Register project
    r = httpx.post(
        f"{BASE}/api/projects",
        json={
            "name": "Food Delivery Application",
            "folder_path": "C:/Projects/FoodDelivery",
            "owner_user_id": user_id,
        },
        timeout=5,
    )
    assert r.status_code == 201, f"Project registration failed: {r.text}"
    project_id = r.json()["project_id"]
    print(f"[OK] Project registered: {project_id}")

    # Ingest event
    r = httpx.post(
        f"{BASE}/api/events",
        json={
            "project_id": project_id,
            "user_id": user_id,
            "role": "DEVELOPER",
            "source": "VS_CODE",
            "event_type": "FILE_MODIFIED",
            "title": "Modified authentication/login.py",
            "description": "File modified in VS Code",
            "status": "INFO",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {"file": "backend/auth/login.py", "file_type": "py"},
        },
        timeout=5,
    )
    assert r.status_code == 201, f"Event ingest failed: {r.text}"
    print(f"[OK] Event ingested: {r.json()['event_id']}")

    # List events
    r = httpx.get(f"{BASE}/api/events?project_id={project_id}", timeout=5)
    assert r.status_code == 200 and len(r.json()) >= 1
    print(f"[OK] Events listed: {len(r.json())} event(s)")

    # Developer summary
    r = httpx.get(
        f"{BASE}/api/projects/{project_id}/summary?user_id={user_id}",
        timeout=5,
    )
    assert r.status_code == 200
    summary = r.json()
    print(f"[OK] Developer summary: {summary['current_status']}")

    # Manager dashboard
    r = httpx.get(
        f"{BASE}/api/projects/{project_id}/dashboard?role=PROJECT_MANAGER",
        timeout=5,
    )
    assert r.status_code == 200
    dashboard = r.json()
    print(f"[OK] Manager dashboard: {dashboard['activity']['total_activities']} activities")

    print("=" * 40)
    print("All Milestone 1 tests passed!")


if __name__ == "__main__":
    main()
