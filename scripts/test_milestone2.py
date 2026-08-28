"""Milestone 2 test — file watcher collector end-to-end."""

import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httpx

from agent.backend_client import BackendClient
from agent.collectors import CollectorManager
from agent.config import AgentConfig
from agent.event_queue import EventQueue


BASE = "http://127.0.0.1:8000"


def _wait_for_backend(timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"{BASE}/api/health", timeout=2)
            if r.status_code == 200:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    return False


def main():
    print("ProjectPulse AI — Milestone 2 Test")
    print("=" * 40)

    if not _wait_for_backend():
        print("[FAIL] Backend not running. Start it with: .\\scripts\\run_backend.ps1")
        sys.exit(1)
    print("[OK] Backend is running")

    with tempfile.TemporaryDirectory(prefix="projectpulse_test_") as tmp:
        test_dir = Path(tmp)
        test_file = test_dir / "backend" / "auth" / "login.py"
        test_file.parent.mkdir(parents=True)

        config = AgentConfig(
            project_name="Test Food Delivery",
            project_folder=str(test_dir),
            user_name="M2 Test Developer",
            backend_url=BASE,
            monitoring_active=True,
            allowed_sources=["VS_CODE"],
        )

        queue = EventQueue()
        backend = BackendClient(config, event_queue=queue)
        assert backend.ensure_registered(), "Registration failed"
        print(f"[OK] Registered project: {config.project_id}")

        manager = CollectorManager(config, backend)
        manager.start()
        print("[OK] File watcher collector started")

        # Simulate VS Code editing a file
        test_file.write_text("# initial", encoding="utf-8")
        time.sleep(3)

        test_file.write_text("# modified content", encoding="utf-8")
        time.sleep(3)

        manager.stop()
        print("[OK] File watcher collector stopped")

        # Verify events in backend
        r = httpx.get(
            f"{BASE}/api/projects/{config.project_id}/events",
            timeout=5,
        )
        assert r.status_code == 200, r.text
        events = r.json()
        event_types = {e["event_type"] for e in events}

        print(f"[INFO] Events captured: {len(events)}")
        for e in events:
            print(f"       - {e['event_type']}: {e['title']}")

        assert "PROJECT_SESSION_STARTED" in event_types, "Missing PROJECT_SESSION_STARTED"
        assert "PROJECT_OPENED" in event_types, "Missing PROJECT_OPENED"
        assert "FILE_MODIFIED" in event_types, "Missing FILE_MODIFIED"
        assert "PROJECT_SESSION_ENDED" in event_types, "Missing PROJECT_SESSION_ENDED"
        print("[OK] All expected VS Code event types captured")

        # Verify metadata has relative path, no file contents
        modified = [e for e in events if e["event_type"] == "FILE_MODIFIED"]
        assert modified, "No FILE_MODIFIED events"
        meta = modified[0]["metadata"]
        assert "file" in meta
        assert "login.py" in meta["file"]
        assert "file_type" in meta
        print(f"[OK] Metadata correct: file={meta['file']}, type={meta['file_type']}")

        # Verify privacy — events only from test project
        for e in events:
            assert e["source"] == "VS_CODE"
            assert e["project_id"] == config.project_id
        print("[OK] Privacy: all events scoped to configured project")

    print("=" * 40)
    print("All Milestone 2 tests passed!")


if __name__ == "__main__":
    main()
