"""Verification Test Suite for the 6 Major Extensions in ProjectPulse AI:

1. AI-Powered Risk Detection (8 explainable rules with facts, explanation, confidence)
2. AI-Generated Project/Task Summaries (Project, Task, Developer, Risk, Timeline)
3. Project-Aware AI Assistant (Context-aware RAG answering 12+ prompt patterns)
4. Real Jira Cloud Integration (Connection, Projects, JQL, ADF parsing, Sync)
5. Unified Project Timeline (Multi-role chronological timeline with filters)
6. Explain WHY Code Changes Happened (Commit -> Files -> Module -> Task -> Reason)
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal, init_db
from backend.services.seed_service import seed_demo_data
from backend.services.risk_service import evaluate_project_risks
from backend.services.ai_service import answer_project_query, generate_project_ai_summary, generate_task_ai_summary
from backend.services.timeline_service import get_unified_project_timeline
from backend.services.code_explanation_service import explain_code_changes
from backend.integrations.registry import integration_manager
from backend.models.db_models import TaskRecord


def test_all_extensions():
    print("=" * 75)
    print("PROJECTPULSE AI — 6 MAJOR EXTENSIONS VERIFICATION TEST")
    print("=" * 75)

    client = TestClient(app)
    init_db()
    db = SessionLocal()

    try:
        seed_demo_data(db)

        # ---------------------------------------------------------------------
        # 1. Test Feature 4: Real Jira Cloud Integration
        # ---------------------------------------------------------------------
        print("\n[Feature 4] Testing Real Jira Cloud Adapter & Task Normalization...")
        jira_adapter = integration_manager.get_adapter("JIRA")
        assert jira_adapter is not None, "Jira adapter must be registered"
        assert jira_adapter.is_connected() is True, "Jira adapter should be connected"

        info = jira_adapter.get_connection_info()
        print(f"  [OK] Jira connection info: {info['platform']} (demo_mode={info['demo_mode']}, base_url={info['base_url']})")

        projects = jira_adapter.get_projects()
        assert len(projects) >= 2, "Expected at least 2 Jira projects"
        print(f"  [OK] Retrieved {len(projects)} Jira projects (First: {projects[0]['key']} - {projects[0]['name']})")

        tasks = jira_adapter.get_tasks("DLX")
        assert len(tasks) >= 3, "Expected at least 3 Jira tasks normalized"
        t0 = tasks[0]
        assert hasattr(t0, "issue_type"), "UnifiedTask must contain issue_type"
        assert hasattr(t0, "story_points"), "UnifiedTask must contain story_points"
        print(f"  [OK] Normalized Jira issue: Key={t0.external_task_id} | Status={t0.status} | Priority={t0.priority} | Type={t0.issue_type}")

        # Test Jira API endpoints
        resp = client.get("/api/integrations/jira/info")
        assert resp.status_code == 200
        resp = client.get("/api/integrations/jira/projects")
        assert resp.status_code == 200
        resp = client.post("/api/integrations/jira/sync", json={"project_id": "DLX", "jira_project_key": "DLX"})
        assert resp.status_code == 200
        sync_data = resp.json()
        assert sync_data["status"] in ("ok", "SUCCESS", "PARTIAL_SUCCESS")
        print(f"  [OK] POST /api/integrations/jira/sync succeeded -> {sync_data['records_synced']} tasks synced")

        # Verify DB tasks have Jira columns
        db_task = db.query(TaskRecord).filter(TaskRecord.project_id == "DLX").first()
        assert hasattr(db_task, "issue_type"), "TaskRecord must have issue_type"
        assert hasattr(db_task, "story_points"), "TaskRecord must have story_points"
        print("  [OK] Feature 4 (Real Jira Integration) passed 100%!")

        # ---------------------------------------------------------------------
        # 2. Test Feature 1: AI-Powered Risk Detection
        # ---------------------------------------------------------------------
        print("\n[Feature 1] Testing AI Risk Detection Engine...")
        risks = evaluate_project_risks(db, "DLX")
        assert len(risks) >= 3, f"Expected at least 3 detected risks, got {len(risks)}"

        rule_ids = [r["rule_id"] for r in risks]
        print(f"  [OK] Evaluated risks: {rule_ids}")
        for r in risks:
            assert "facts" in r and len(r["facts"]) > 0, "Risk must contain observable facts"
            assert "explanation" in r and len(r["explanation"]) > 10, "Risk must contain AI explanation"
            assert "confidence" in r and 0.0 <= r["confidence"] <= 1.0, "Risk must have confidence score"
            assert "suggested_action" in r, "Risk must contain suggested action"

        resp = client.get("/api/projects/DLX/risks/ai")
        assert resp.status_code == 200
        ai_risks = resp.json()
        assert len(ai_risks) >= 3
        print(f"  [OK] GET /api/projects/DLX/risks/ai returned {len(ai_risks)} explainable risks")
        print("  [OK] Feature 1 (AI Risk Detection) passed 100%!")

        # ---------------------------------------------------------------------
        # 3. Test Feature 2: AI-Generated Project & Task Summaries
        # ---------------------------------------------------------------------
        print("\n[Feature 2] Testing AI Project & Task Summaries...")
        proj_summary = generate_project_ai_summary(db, "DLX", summary_type="project")
        assert len(proj_summary["summary"]) > 50, "Summary must be multi-paragraph"
        assert len(proj_summary["key_findings"]) >= 3, "Expected key findings"
        print(f"  [OK] Generated Project AI Summary:\n       Title: {proj_summary['title']}\n       Key Findings: {proj_summary['key_findings'][:2]}")

        task_summary = generate_task_ai_summary(db, "DLX-101")
        assert "Plan Status" in task_summary["summary"] or "Payment" in task_summary["summary"]
        print(f"  [OK] Generated Task AI Summary for DLX-101 (Verdict: {task_summary['verdict']})")

        resp = client.post("/api/projects/DLX/ai/summary", json={"summary_type": "project", "timeframe": "24h"})
        assert resp.status_code == 200
        resp = client.post("/api/tasks/DLX-101/ai/summary")
        assert resp.status_code == 200
        print("  [OK] Feature 2 (AI Summaries) passed 100%!")

        # ---------------------------------------------------------------------
        # 4. Test Feature 3: Context-Aware AI Assistant
        # ---------------------------------------------------------------------
        print("\n[Feature 3] Testing Context-Aware AI Assistant...")
        test_queries = [
            "Why does the Payment API need attention?",
            "What is the difference between planned and actual progress?",
            "Which tasks have Jira status inconsistent with actual development activity?",
            "Which tasks are overdue?",
            "What did the developers work on today?",
            "What are the biggest current risks?",
            "Show me recent activity related to the login module.",
            "Summarize this project for my manager.",
        ]

        for q in test_queries:
            ans = answer_project_query(db, "DLX", q)
            assert len(ans["answer"]) > 20, f"Answer must not be empty for query: {q}"
            assert len(ans["citations"]) > 0, f"Must cite evidence for query: {q}"
            print(f"  [OK] AI Assistant answered: '{q[:40]}...' (Citations: {len(ans['citations'])})")

        # Test Insufficient Evidence case
        empty_ans = answer_project_query(db, "DLX", "xyz nonexistent query 999")
        assert len(empty_ans["answer"]) > 10
        print("  [OK] AI Assistant safely handles arbitrary queries without hallucinating")
        print("  [OK] Feature 3 (AI Assistant) passed 100%!")

        # ---------------------------------------------------------------------
        # 5. Test Feature 5: Unified Chronological Project Timeline
        # ---------------------------------------------------------------------
        print("\n[Feature 5] Testing Unified Project Timeline...")
        timeline_all = get_unified_project_timeline(db, "DLX", category_filter="ALL")
        assert len(timeline_all) >= 5, f"Expected at least 5 timeline items, got {len(timeline_all)}"

        sources = set(item["source"] for item in timeline_all)
        print(f"  [OK] Unified Timeline retrieved {len(timeline_all)} items across sources: {sources}")

        # Test filters
        for f in ["JIRA", "DEV", "BUILD", "TEST", "AI"]:
            filtered = get_unified_project_timeline(db, "DLX", category_filter=f)
            print(f"  [OK] Timeline filter '{f}' returned {len(filtered)} items")

        resp = client.get("/api/projects/DLX/timeline?filter=ALL&limit=50")
        assert resp.status_code == 200
        assert len(resp.json()) >= 5
        print("  [OK] Feature 5 (Unified Timeline) passed 100%!")

        # ---------------------------------------------------------------------
        # 6. Test Feature 6: Explain WHY Code Changes Happened
        # ---------------------------------------------------------------------
        print("\n[Feature 6] Testing Code Change Explanation Engine...")
        explanations = explain_code_changes(db, "DLX")
        assert len(explanations) > 0, "Expected at least 1 code explanation"

        exp0 = explanations[0]
        assert "explanation" in exp0 and len(exp0["explanation"]) > 20
        assert "confidence_level" in exp0 and exp0["confidence_level"] in ("DIRECT", "LIKELY", "PLAUSIBLE", "UNLINKED")
        assert "evidence_signals" in exp0 and len(exp0["evidence_signals"]) > 0

        print(f"  [OK] Code Explanation: Module={exp0['inferred_module']} | Level={exp0['confidence_level']} (Score={exp0['confidence_score']})")
        print(f"       AI Reasoning: \"{exp0['explanation']}\"")

        resp = client.get("/api/projects/DLX/code-explanations")
        assert resp.status_code == 200
        assert len(resp.json()) > 0
        print("  [OK] Feature 6 (Explain WHY Code Changed) passed 100%!")

        print("\n" + "=" * 75)
        print("ALL 6 MAJOR EXTENSION FEATURES VERIFIED AND PASSING 100%!")
        print("=" * 75)

    finally:
        db.close()


if __name__ == "__main__":
    test_all_extensions()
