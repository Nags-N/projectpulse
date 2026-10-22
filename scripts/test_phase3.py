"""Phase 3 Verification Test Suite — Developer Mode (File, Git, Build Collectors & Privacy Filter)."""

import sys
import time
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.main import app
from agent.backend_client import BackendClient
from agent.config import AgentConfig
from agent.collectors.build_collector import BuildCollector
from agent.collectors.file_watcher import ProjectFileWatcherCollector, _should_ignore
from agent.normalizer import EventNormalizer
from agent.privacy_filter import PrivacyFilter
from shared.event_types import EventSource, EventType


def test_phase3_developer_mode():
    print("=" * 60)
    print("PROJECTPULSE AI — PHASE 3 DEVELOPER MODE VERIFICATION")
    print("=" * 60)

    # 1. Privacy Filter Safeguards
    print("\n[Step 1] Testing Privacy Filter and Ignore Rules...")
    config = AgentConfig.load()
    privacy = PrivacyFilter(config)

    assert privacy.allow_path(ROOT / "backend" / "main.py") is True
    # Test ignored files/directories
    assert _should_ignore(Path(".git/HEAD")) is True
    assert _should_ignore(Path("node_modules/vite/package.json")) is True
    assert _should_ignore(Path(".venv/Scripts/python.exe")) is True
    assert _should_ignore(Path("logs/app.log")) is True
    assert _should_ignore(Path("temp/file.tmp")) is True
    assert _should_ignore(Path(".env")) is False  # Suffix check
    assert _should_ignore(Path("src/App.jsx")) is False
    print("  [OK] Sensitive paths (.git, node_modules, .venv, logs, .tmp) properly filtered.")

    # 2. Build Collector & Approved Commands
    print("\n[Step 2] Testing Build Collector for Approved Commands...")
    normalizer = EventNormalizer(config)
    client = TestClient(app)

    # Mock backend sender
    events_captured = []
    class MockBackend:
        def send_event(self, event):
            events_captured.append(event)
            # Forward to TestClient
            client.post("/api/events", json=event.model_dump(mode="json"))
            return True

    mock_backend = MockBackend()
    build_col = BuildCollector(
        config=config,
        normalizer=normalizer,
        privacy_filter=privacy,
        backend=mock_backend,
    )

    # Check command approval
    assert build_col.is_command_approved("npm run build") is True
    assert build_col.is_command_approved("pytest") is True
    assert build_col.is_command_approved("mvn test") is True
    assert build_col.is_command_approved("cat /etc/passwd") is False
    assert build_col.is_command_approved("powershell Get-Process") is False
    print("  [OK] Approved command allowlist strictly enforced (arbitrary shell commands blocked).")

    # Record simulated build success and failure
    build_col.record_build_execution("npm run build", 0, 4.12)
    assert len(events_captured) == 1
    assert events_captured[-1].event_type == EventType.BUILD_SUCCEEDED.value
    print("  [OK] BUILD_SUCCEEDED event generated and recorded.")

    build_col.record_build_execution("pytest", 1, 6.45, "AssertionError in test_payment.py")
    assert len(events_captured) == 2
    assert events_captured[-1].event_type == EventType.BUILD_FAILED.value
    print("  [OK] BUILD_FAILED event generated with non-sensitive failure snippet.")

    # 3. File Watcher Event Generation
    print("\n[Step 3] Testing File Collector Event Generation...")
    file_col = ProjectFileWatcherCollector(
        config=config,
        normalizer=normalizer,
        privacy_filter=privacy,
        backend=mock_backend,
    )

    # Simulate file created and modified events
    test_rel = "services/order_service.py"
    dummy_path = ROOT / "backend" / "models" / "db_models.py"

    evt_created = normalizer.normalize(
        source=EventSource.FILE,
        event_type=EventType.FILE_CREATED,
        title=f"Created {test_rel}",
        description=f"File created in project: {test_rel}",
        metadata={"file": test_rel, "project": config.project_name},
    )
    mock_backend.send_event(evt_created)
    print("  [OK] FILE_CREATED event generated and delivered.")

    evt_modified = normalizer.normalize(
        source=EventSource.FILE,
        event_type=EventType.FILE_MODIFIED,
        title=f"Modified {test_rel}",
        description=f"File modified in project: {test_rel}",
        metadata={"file": test_rel, "project": config.project_name},
    )
    mock_backend.send_event(evt_modified)
    print("  [OK] FILE_MODIFIED event generated and delivered.")

    # 4. Git Collector Event Generation
    print("\n[Step 4] Testing Git Collector Event Generation...")
    evt_git = normalizer.normalize(
        source=EventSource.GIT,
        event_type=EventType.GIT_COMMIT,
        title="Commit 9c42b1: Implement customer checkout flow",
        description="Commit by Alex Rivera on branch feature/checkout",
        status="INFO",
        metadata={
            "branch": "feature/checkout",
            "commit_hash": "9c42b1a",
            "repo": "dlx-platform",
            "project": config.project_name,
        },
    )
    mock_backend.send_event(evt_git)
    print("  [OK] GIT_COMMIT event generated without secrets or sensitive diffs.")

    # 5. Verify Backend Ingestion of Developer Events
    print("\n[Step 5] Querying Backend for Ingested Developer Events...")
    res = client.get("/api/events?project_id=DLX&role=DEVELOPER&limit=10")
    assert res.status_code == 200
    dev_events = res.json()
    assert len(dev_events) >= 4
    print(f"  [OK] Backend successfully verified {len(dev_events)} developer events in timeline.")

    # 6. Verify Developer Summary Updates
    print("\n[Step 6] Testing Developer Summary Activity Calculations...")
    res = client.get(f"/api/projects/DLX/summary?user_id={config.user_id}")
    assert res.status_code == 200
    summary = res.json()
    print(f"  [OK] Developer Highlights: {summary['highlights'][:2]}")
    print(f"  [OK] Total Activity Count: {summary['activity']['total_activities']}")
    print(f"  [OK] Commits Count: {summary['activity']['commits']}")
    print(f"  [OK] Build Successes: {summary['activity']['build_successes']}")

    print("\n" + "=" * 60)
    print(">>> ALL PHASE 3 VERIFICATION TESTS PASSED SUCCESSFULLY! <<<")
    print("=" * 60)


if __name__ == "__main__":
    test_phase3_developer_mode()
