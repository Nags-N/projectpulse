"""Multi-Agent Local Simulator for ProjectPulse AI.

Simulates multiple distinct team agents (Developer, Tester, QA) on a single physical machine
in accordance with Section 49 & 50 of the Master Architecture Specification.
"""

import argparse
import sys
import time
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx
from shared.event_types import EventSource, EventType, UserRole
from shared.timeutil import to_iso_utc, utc_now

DEFAULT_BACKEND = "http://127.0.0.1:8000"
PROJECT_ID = "DLX"


AGENTS = [
    {
        "agent_id": "AGENT-DEV-001",
        "user_id": "DEV-001",
        "user_name": "Alex Rivera",
        "role": UserRole.DEVELOPER.value,
        "machine_name": "DEV-LAPTOP-ALEX",
        "machine_id": "MAC-01",
    },
    {
        "agent_id": "AGENT-DEV-002",
        "user_id": "DEV-002",
        "user_name": "Marcus Vance",
        "role": UserRole.DEVELOPER.value,
        "machine_name": "DEV-DESKTOP-MARCUS",
        "machine_id": "MAC-02",
    },
    {
        "agent_id": "AGENT-TEST-001",
        "user_id": "TEST-001",
        "user_name": "Dave Miller",
        "role": UserRole.TESTER.value,
        "machine_name": "TEST-STATION-DAVE",
        "machine_id": "MAC-03",
    },
    {
        "agent_id": "AGENT-QA-001",
        "user_id": "QA-001",
        "user_name": "Liam Johnson",
        "role": UserRole.QA.value,
        "machine_name": "QA-RIG-LIAM",
        "machine_id": "MAC-04",
    },
]


def register_all_agents(backend_url: str):
    print(f"[*] Registering {len(AGENTS)} agents with backend at {backend_url}...")
    with httpx.Client(timeout=5.0) as client:
        for agent in AGENTS:
            payload = {
                "agent_id": agent["agent_id"],
                "user_id": agent["user_id"],
                "project_id": PROJECT_ID,
                "role": agent["role"],
                "machine_name": agent["machine_name"],
                "machine_id": agent["machine_id"],
            }
            try:
                res = client.post(f"{backend_url}/api/agents/register", json=payload)
                if res.status_code in (200, 201):
                    print(f"  [OK] Registered {agent['agent_id']} ({agent['role']}) on {agent['machine_name']}")
                else:
                    print(f"  [WARN] Failed to register {agent['agent_id']}: {res.status_code}")
            except Exception as e:
                print(f"  [ERROR] Connection failed for {agent['agent_id']}: {e}")


def send_heartbeats(backend_url: str):
    with httpx.Client(timeout=3.0) as client:
        for agent in AGENTS:
            payload = {
                "agent_id": agent["agent_id"],
                "monitoring_active": True,
            }
            try:
                client.post(f"{backend_url}/api/agents/heartbeat", json=payload)
            except Exception:
                pass


def emit_demo_scenario_events(backend_url: str):
    """Emit the Section 50 Demo Storyline Events."""
    print("\n[*] Emitting cross-role storyline events to backend...")
    now_str = to_iso_utc(utc_now())

    story_events = [
        # Developer Event
        {
            "agent_id": "AGENT-DEV-001",
            "user_id": "DEV-001",
            "project_id": PROJECT_ID,
            "role": UserRole.DEVELOPER.value,
            "source": EventSource.GIT.value,
            "event_type": EventType.GIT_COMMIT.value,
            "title": "Commit 82e1c9: Refactored payment retry and session webhook",
            "description": "Added exponential backoff and Stripe signature verification",
            "status": "INFO",
            "timestamp": now_str,
            "metadata": {"branch": "feature/payment-v2", "commit_hash": "82e1c9"},
        },
        # Developer Build Event
        {
            "agent_id": "AGENT-DEV-001",
            "user_id": "DEV-001",
            "project_id": PROJECT_ID,
            "role": UserRole.DEVELOPER.value,
            "source": EventSource.BUILD.value,
            "event_type": EventType.BUILD_SUCCEEDED.value,
            "title": "Build succeeded: npm run build",
            "description": "Production build passed in 3.8s",
            "status": "SUCCESS",
            "timestamp": now_str,
            "metadata": {"command": "npm run build", "exit_code": 0},
        },
        # Tester Event
        {
            "agent_id": "AGENT-TEST-001",
            "user_id": "TEST-001",
            "project_id": PROJECT_ID,
            "role": UserRole.TESTER.value,
            "source": EventSource.TEST.value,
            "event_type": EventType.TEST_FAILED.value,
            "title": "pytest PaymentTests: 2 tests failed (504 Timeout not caught)",
            "description": "test_payment_gateway_timeout and test_concurrent_idempotency failed",
            "status": "WARNING",
            "timestamp": now_str,
            "metadata": {"framework": "pytest", "suite": "PaymentTests", "failed": 2, "passed": 18, "duration": 14.2},
        },
        # QA Event
        {
            "agent_id": "AGENT-QA-001",
            "user_id": "QA-001",
            "project_id": PROJECT_ID,
            "role": UserRole.QA.value,
            "source": EventSource.QA.value,
            "event_type": EventType.BUG_REPORTED.value,
            "title": "CRITICAL Defect: Payment duplicate charge on checkout double-click",
            "description": "Button is not immediately disabled; user charged twice when pressing button repeatedly",
            "status": "ERROR",
            "timestamp": now_str,
            "metadata": {"severity": "CRITICAL", "module": "Payment Gateway", "priority": "HIGH"},
        },
    ]

    with httpx.Client(timeout=5.0) as client:
        for evt in story_events:
            try:
                res = client.post(f"{backend_url}/api/events", json=evt)
                if res.status_code == 201:
                    print(f"  [OK] {evt['role']} -> {evt['title']}")
                else:
                    print(f"  [WARN] Backend rejected event: {res.status_code}")
            except Exception as e:
                print(f"  [ERROR] Failed to send event: {e}")


def main():
    parser = argparse.ArgumentParser(description="ProjectPulse Multi-Agent Local Simulator")
    parser.add_argument("--backend", default=DEFAULT_BACKEND, help="Backend URL")
    parser.add_argument("--loop", action="store_true", help="Keep sending heartbeats periodically")
    parser.add_argument("--interval", type=int, default=10, help="Heartbeat interval in seconds")
    parser.add_argument("--emit-events", action="store_true", default=True, help="Emit demo scenario events")
    args = parser.parse_args()

    print("=" * 60)
    print("PROJECTPULSE AI — MULTI-AGENT LOCAL SIMULATOR")
    print("=" * 60)

    register_all_agents(args.backend)
    send_heartbeats(args.backend)

    if args.emit_events:
        emit_demo_scenario_events(args.backend)

    if args.loop:
        print(f"\n[*] Keeping agents active with heartbeats every {args.interval}s (Ctrl+C to stop)...")
        try:
            while True:
                time.sleep(args.interval)
                send_heartbeats(args.backend)
                print(".", end="", flush=True)
        except KeyboardInterrupt:
            print("\nSimulator stopped.")


if __name__ == "__main__":
    main()
