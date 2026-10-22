"""Verification script for Phase 14 & 15: AI Project Assistant & RAG Engine."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.services.seed_service import seed_demo_data
from backend.services.ai_service import answer_project_query, get_ai_suggestions, retrieve_context

def main():
    print("[TEST] Running Phase 14 & 15 AI Assistant verification...")

    client = TestClient(app)
    db = SessionLocal()
    try:
        seed_demo_data(db)

        # 1. Test Suggestions API
        resp = client.get("/api/projects/DLX/ai/suggestions")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        suggestions = resp.json().get("suggestions", [])
        assert len(suggestions) > 3, "Expected at least 4 suggestions"
        print(f"[OK] AI suggestions retrieved: {len(suggestions)} suggestions available")

        # 2. Test Context Retrieval
        ctx = retrieve_context(db, "DLX", "payment tests defect")
        assert len(ctx["tasks"]) > 0, "Expected matched tasks"
        assert len(ctx["defects"]) > 0, "Expected matched defects"
        assert len(ctx["events"]) > 0, "Expected matched events"
        print(f"[OK] RAG Context retrieval succeeded (Tasks: {len(ctx['tasks'])}, Defects: {len(ctx['defects'])}, Events: {len(ctx['events'])})")

        # 3. Test Section 57 Demo Question: "Why does the Payment API need attention?"
        ans1 = answer_project_query(db, "DLX", "Why does the Payment API need attention?")
        assert len(ans1["citations"]) > 0, "Expected evidence citations"
        assert "Payment" in ans1["answer"], "Expected payment in answer"
        assert "DLX-101" in " ".join(ans1["citations"]), "Expected citation to DLX-101"
        print("[OK] Section 57 Question 1 ('Why does Payment API need attention?') successfully answered with citations:")
        for c in ans1["citations"]:
            print(f"     - Citation: {c}")

        # 4. Test "What is the difference between planned and actual progress?"
        ans2 = answer_project_query(db, "DLX", "What is the difference between planned and actual progress?")
        assert "Plan vs Reality" in ans2["answer"], "Expected Plan vs Reality analysis in answer"
        print("[OK] Plan vs Reality progress query successfully answered.")

        # 5. Test "What are the current testing problems?"
        ans3 = answer_project_query(db, "DLX", "What are the current testing problems?")
        assert "Testing" in ans3["answer"] or "test" in ans3["answer"].lower(), "Expected testing in answer"
        print("[OK] Testing problems query successfully answered.")

        # 6. Test "What are the major QA issues?"
        ans4 = answer_project_query(db, "DLX", "What are the major QA issues?")
        assert "DEF-" in ans4["answer"] or "Defect" in ans4["answer"], "Expected defect in answer"
        print("[OK] QA issues query successfully answered.")

        # 7. Test AI Chat API Endpoint
        api_resp = client.post("/api/projects/DLX/ai/chat", json={"query": "Why does the Payment API need attention?"})
        assert api_resp.status_code == 200, f"Expected 200, got {api_resp.status_code}"
        payload = api_resp.json()
        assert "answer" in payload
        assert len(payload["citations"]) > 0
        print("[OK] FastAPI endpoint /api/projects/DLX/ai/chat verified successfully.")

        print("\n[ALL TESTS PASSED] Phase 14 & 15 AI Project Assistant verified!")
    finally:
        db.close()

if __name__ == "__main__":
    main()
