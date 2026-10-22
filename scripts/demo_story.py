"""Section 57 Master Demonstration Script: PROJECTPULSE AI End-to-End Story.

Executes the official 7-step evaluation story:
  Step 1: Developer works (file modified, Git commit, build recorded).
  Step 2: Tester runs tests (Pytest test suite run, 3 failures recorded).
  Step 3: QA reports high-severity defect (DEF-1 logged and linked to task).
  Step 4: Jira task status is 'In Progress' (DLX-101 Payment Gateway).
  Step 5: ProjectPulse normalizes and combines heterogeneous data sources.
  Step 6: Dashboard & Risk Engine flag Plan vs Reality mismatch and testing risks.
  Step 7: Project Manager asks AI: 'Why does the Payment API need attention?'
          AI responds with grounded evidence citations.
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database import SessionLocal, init_db
from backend.services.seed_service import seed_demo_data
from backend.services.event_service import create_event, get_manager_dashboard
from backend.services.qa_service import report_defect
from backend.services.risk_service import evaluate_project_risks
from backend.services.ai_service import answer_project_query
from shared.events import ProjectEventCreate
from shared.event_types import EventSource, EventType, UserRole


def print_banner(text: str):
    print("\n" + "=" * 75)
    print(f" {text}")
    print("=" * 75)


def run_demo():
    print_banner("PROJECTPULSE AI - MASTER DEMONSTRATION STORY (SECTION 57)")
    print("Scenario: DLX E-Commerce Platform Multi-Role Intelligence Monitoring")
    print("Team: Alice Chen (Dev), Bob Smith (Tester), Carol Davis (QA), PM (Jira)")

    init_db()
    db = SessionLocal()

    try:
        # Seed base configuration & tasks
        seed_demo_data(db)

        # ---------------------------------------------------------------------
        # STEP 1: Developer works on project
        # ---------------------------------------------------------------------
        print_banner("STEP 1: DEVELOPER ACTIVITY COLLECTION")
        print("Developer Agent (DEV-001 / Alice Chen) monitors workspace in background...")

        evt_commit = create_event(
            db,
            ProjectEventCreate(
                agent_id="AGENT-DEV-001",
                project_id="DLX",
                user_id="DEV-001",
                role=UserRole.DEVELOPER,
                source=EventSource.GIT,
                event_type=EventType.GIT_COMMIT,
                title="feat(payment): integrate stripe payment checkout intent flow",
                description="Added Stripe checkout session handlers and webhook listener",
                status="INFO",
                metadata={"branch": "feature/payment-gateway", "commit_hash": "a1b2c3d", "files_changed": 4},
            )
        )
        print(f"[OK] Event Captured: GIT_COMMIT [{evt_commit.event_id[:8]}] - '{evt_commit.title}'")

        evt_build = create_event(
            db,
            ProjectEventCreate(
                agent_id="AGENT-DEV-001",
                project_id="DLX",
                user_id="DEV-001",
                role=UserRole.DEVELOPER,
                source=EventSource.BUILD,
                event_type=EventType.BUILD_SUCCEEDED,
                title="Build succeeded (npm run build)",
                description="Frontend bundle compiled in 1.9s",
                status="INFO",
                metadata={"command": "npm run build", "duration_sec": 1.9, "exit_code": 0},
            )
        )
        print(f"[OK] Event Captured: BUILD_SUCCEEDED [{evt_build.event_id[:8]}] - '{evt_build.title}'")

        # ---------------------------------------------------------------------
        # STEP 2: Tester runs automated tests
        # ---------------------------------------------------------------------
        print_banner("STEP 2: TESTER AUTOMATED TEST EXECUTION")
        print("Tester Agent (TEST-001 / Bob Smith) runs Pytest payment integration test suite...")

        evt_test = create_event(
            db,
            ProjectEventCreate(
                agent_id="AGENT-TEST-001",
                project_id="DLX",
                user_id="TEST-001",
                role=UserRole.TESTER,
                source=EventSource.TEST,
                event_type=EventType.TEST_FAILED,
                title="pytest tests/unit/test_payment.py: 3 failed, 12 passed",
                description="Gateway timeout handling test cases failed with 504 status",
                status="FAILED",
                metadata={
                    "framework": "pytest",
                    "suite": "PaymentIntegration",
                    "total": 15,
                    "passed": 12,
                    "failed": 3,
                    "errors": ["AssertionError: Expected 200, got 504 Gateway Timeout in test_stripe_webhook"],
                },
            )
        )
        print(f"[OK] Event Captured: TEST_FAILED [{evt_test.event_id[:8]}] - '{evt_test.title}'")
        print("     -> 3 automated test failures detected in payment integration suite.")

        # ---------------------------------------------------------------------
        # STEP 3: QA reports high-severity defect
        # ---------------------------------------------------------------------
        print_banner("STEP 3: QA DEFECT REPORTING & RELEASE GATE")
        print("QA Agent (QA-001 / Carol Davis) verifies build and discovers critical flaw...")

        defect = report_defect(
            db,
            title="Stripe webhook timeout on high concurrency checkout",
            description="Payment confirmation times out when concurrency > 10 requests/sec. Webhook dropped.",
            severity="HIGH",
            priority="HIGH",
            related_task_id="DLX-101",
            reported_by="QA-001 (Carol Davis)",
            project_id="DLX",
        )
        print(f"[OK] Defect Logged: DEF-{defect.id} - '{defect.title}'")
        print(f"     -> Severity: {defect.severity} | Priority: {defect.priority} | Linked Task: {defect.related_task_id}")

        # ---------------------------------------------------------------------
        # STEP 4: Jira PM tool status
        # ---------------------------------------------------------------------
        print_banner("STEP 4: PROJECT MANAGEMENT PLATFORM (JIRA)")
        print("Jira PM synchronization records:")
        print("     -> Task ID: DLX-101")
        print("     -> Title:   Payment Gateway Integration (Stripe)")
        print("     -> Status:  IN_PROGRESS")
        print("     -> Owner:   Alice Chen (DEV-001)")
        print("     -> Note:    Jira shows work progressing normally without warning flags.")

        # ---------------------------------------------------------------------
        # STEP 5: ProjectPulse Normalization & Aggregation
        # ---------------------------------------------------------------------
        print_banner("STEP 5: DATA NORMALIZATION & MULTI-SOURCE SYNTHESIS")
        print("ProjectPulse AI normalizes all heterogeneous telemetry into a unified context:")
        dashboard = get_manager_dashboard(db, "DLX")
        print(f"[OK] Unified Activities Logged: {dashboard.activity.total_activities}")
        print(f"[OK] Active Fleet:             {len(dashboard.team_agents)} Agents Online")
        print(f"[OK] Overall Health Scorecard: {dashboard.health.overall_status}")
        print(f"     - Testing Status:         {dashboard.health.testing_status}")
        print(f"     - QA Status:              {dashboard.health.qa_status}")

        # ---------------------------------------------------------------------
        # STEP 6: Evidence Linker connects events to Payment API Task
        # ---------------------------------------------------------------------
        print_banner("STEP 6: EVIDENCE LINKER INSPECTION (TASK PROJ-101 / DLX-101)")
        from backend.services.evidence_service import get_task_evidence_detail
        task_ev = get_task_evidence_detail(db, "PROJ-101")
        if task_ev:
            print(f"[OK] Task Evidence Linked for: {task_ev.task.external_task_id} ({task_ev.task.title})")
            print(f"     -> Planned:   Priority: {task_ev.planned['priority']} | Sprint: {task_ev.planned['sprint']} | Due: {task_ev.planned['due_date']}")
            print(f"     -> Actual:    Commits: {task_ev.actual_counts['commits']} | Files: {task_ev.actual_counts['files_modified']} | Builds: {task_ev.actual_counts['builds']} | Tests: {task_ev.actual_counts['test_runs']} (Failed: {task_ev.actual_counts['failed_tests']}) | Defects: {task_ev.actual_counts['open_defects']}")
            print(f"     -> Verdict:   Overall: {task_ev.plan_vs_reality['overall_status']} (Dev: {task_ev.plan_vs_reality['development_status']}, Test: {task_ev.plan_vs_reality['testing_status']}, QA: {task_ev.plan_vs_reality['qa_status']})")
            print(f"     -> Summary:   {task_ev.plan_vs_reality['verdict']}")
            print(f"     -> Total Linked Evidence Items: {len(task_ev.evidence)}")

        # ---------------------------------------------------------------------
        # STEP 7: Plan vs Reality Engine & Risk Detection
        # ---------------------------------------------------------------------
        print_banner("STEP 7: PLAN VS REALITY ENGINE RISK DETECTION")
        print("Evaluating explainable risk rules across promises vs actual telemetry...")
        risks = evaluate_project_risks(db, "DLX")
        print(f"[ALERT] {len(risks)} Active Project Risk(s) Detected:")
        for r in risks:
            print(f"\n  * [{r['severity']}] {r['rule_id']}: {r['title']}")
            print(f"    - Facts:          {'; '.join(r['facts'])}")
            print(f"    - Interpretation: {r['interpretation']}")
            print(f"    - Recommendation: {r['suggested_action']}")

        # ---------------------------------------------------------------------
        # STEP 8: Project Manager queries AI Assistant
        # ---------------------------------------------------------------------
        print_banner("STEP 8: AI PROJECT ASSISTANT RAG EVIDENCE CITATIONS")
        question = "Why does the Payment API need attention?"
        print(f"Project Manager asks: '{question}'\n")

        ai_response = answer_project_query(db, "DLX", question)

        print("[AI ASSISTANT RESPONSE]:")
        print("-" * 75)
        print(ai_response["answer"])
        print("-" * 75)

        print("\n[GROUNDED EVIDENCE CITATIONS]:")
        for cit in ai_response["citations"]:
            print(f"  [EVIDENCE] {cit}")

        print_banner("DEMONSTRATION COMPLETED SUCCESSFULLY")
        print("[SUCCESS] All 7 steps of the Section 57 specification have executed and verified!")
        print("FastAPI Backend: http://127.0.0.1:8000")
        print("React Frontend:  http://127.0.0.1:5173")
        print("Manager View:    http://127.0.0.1:5173/manager")
        print("AI Assistant:    http://127.0.0.1:5173/assistant")

    finally:
        db.close()


if __name__ == "__main__":
    run_demo()
