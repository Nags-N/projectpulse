"""Milestone 3 test — Git activity collector end-to-end."""

import subprocess
import sys
import tempfile
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


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)


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


def _git_available() -> bool:
    try:
        subprocess.run(["git", "--version"], capture_output=True, timeout=3, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def main():
    print("ProjectPulse AI — Milestone 3 Test")
    print("=" * 40)

    if not _git_available():
        print("[FAIL] Git is not installed or not in PATH")
        sys.exit(1)
    print("[OK] Git is available")

    if not _wait_for_backend():
        print("[FAIL] Backend not running. Start it with: .\\scripts\\run_backend.ps1")
        sys.exit(1)
    print("[OK] Backend is running")

    with tempfile.TemporaryDirectory(prefix="projectpulse_git_") as tmp:
        repo = Path(tmp)

        _run(["git", "init"], repo)
        _run(["git", "config", "user.email", "test@projectpulse.local"], repo)
        _run(["git", "config", "user.name", "M3 Tester"], repo)

        sample = repo / "backend" / "auth" / "login.py"
        sample.parent.mkdir(parents=True)
        sample.write_text("print('login')\n", encoding="utf-8")
        _run(["git", "add", "."], repo)
        _run(["git", "commit", "-m", "Initial commit"], repo)

        config = AgentConfig(
            project_name="Git Test Project",
            project_folder=str(repo),
            user_name="M3 Git Tester",
            backend_url=BASE,
            monitoring_active=True,
            allowed_sources=["GIT"],
        )

        queue = EventQueue()
        backend = BackendClient(config, event_queue=queue)
        assert backend.ensure_registered(), "Registration failed"
        print(f"[OK] Registered project: {config.project_id}")

        manager = CollectorManager(config, backend)
        manager.start()
        print("[OK] Git collector started")

        # Branch change + commit
        _run(["git", "checkout", "-b", "feature/payment"], repo)
        time.sleep(3)

        sample.write_text("print('payment')\n", encoding="utf-8")
        _run(["git", "add", "backend/auth/login.py"], repo)
        _run(["git", "commit", "-m", "Add payment module"], repo)
        time.sleep(3)

        # Simulate pull signal via FETCH_HEAD creation
        fetch_head = repo / ".git" / "FETCH_HEAD"
        fetch_head.write_text("abc123\trefs/heads/main\n", encoding="utf-8")
        time.sleep(3)

        # Simulate push via project-local push log
        push_log = repo / ".git" / "projectpulse" / "push.log"
        push_log.parent.mkdir(exist_ok=True)
        with push_log.open("a", encoding="utf-8") as f:
            f.write("PUSH|feature/payment|abc123def456|origin\n")
        time.sleep(3)

        manager.stop()
        print("[OK] Git collector stopped")

        r = httpx.get(f"{BASE}/api/projects/{config.project_id}/events", timeout=5)
        assert r.status_code == 200, r.text
        events = r.json()
        event_types = {e["event_type"] for e in events}

        print(f"[INFO] Events captured: {len(events)}")
        for e in events:
            meta = e.get("metadata", {})
            branch = meta.get("branch", "")
            print(f"       - {e['event_type']}: {e['title']} [{branch}]")

        required = {
            "GIT_BRANCH_CREATED",
            "GIT_BRANCH_CHANGED",
            "GIT_COMMIT",
            "GIT_PULL",
            "GIT_PUSH",
        }
        missing = required - event_types
        assert not missing, f"Missing event types: {missing}"
        print("[OK] All required Git event types captured")

        commits = [e for e in events if e["event_type"] == "GIT_COMMIT"]
        assert commits[0]["metadata"].get("commit_hash"), "Commit hash missing"
        print(f"[OK] Commit hash captured: {commits[0]['metadata']['commit_hash'][:8]}...")

        for e in events:
            assert e["source"] == "GIT"
            assert e["project_id"] == config.project_id
        print("[OK] Privacy: all events scoped to configured project repo")

    print("=" * 40)
    print("All Milestone 3 tests passed!")


if __name__ == "__main__":
    main()
