"""Evidence Linker Service.

Implements Sections 5, 17, 30 & Feature 1, 4:
- Connects real engineering events (Git, files, builds, tests, QA) to PM tasks.
- Persists explicit EvidenceRecord rows with confidence scores.
- Calculates per-task actual evidence counts and Plan vs Reality status.
"""

import json
import re
from datetime import datetime
from typing import Any
from sqlalchemy.orm import Session

from backend.database import metadata_from_json, metadata_to_json
from backend.models.db_models import (
    DefectRecord,
    EvidenceRecord,
    ProjectEventRecord,
    TaskRecord,
)
from backend.models.schemas import (
    EvidenceResponse,
    TaskEvidenceDetailResponse,
    TaskResponse,
    new_id,
)
from shared.event_types import EventSource, EventType


def link_event_to_tasks(db: Session, event: ProjectEventRecord) -> list[EvidenceRecord]:
    """Analyze an event and link it as Evidence to relevant task(s)."""
    text_corpus = f"{event.title} {event.description}".lower()
    meta = metadata_from_json(event.metadata_json)
    for v in meta.values():
        if isinstance(v, (str, int)):
            text_corpus += f" {v}".lower()

    tasks = db.query(TaskRecord).filter(TaskRecord.project_id == event.project_id).all()
    created_evidence: list[EvidenceRecord] = []

    for task in tasks:
        ext_id = task.external_task_id.lower()
        confidence = 0.0
        reason = ""

        # 1. Exact Task Key match (e.g. "DLX-101", "PROJ-101")
        if ext_id in text_corpus:
            confidence = 1.0
            reason = f"Explicit task key match ({task.external_task_id})"
        # 2. Defect related_task_id link
        elif event.source == "QA" and meta.get("related_task_id", "").lower() == ext_id:
            confidence = 1.0
            reason = f"QA Defect linked to {task.external_task_id}"
        # 3. High keyword overlap in title
        else:
            task_words = [w for w in re.findall(r"\w+", task.title.lower()) if len(w) > 4]
            matching_words = [w for w in task_words if w in text_corpus]
            if matching_words:
                confidence = 0.85
                reason = f"Keyword match: {', '.join(matching_words)}"

        if confidence > 0.0:
            # Check if this evidence is already recorded
            existing = (
                db.query(EvidenceRecord)
                .filter(
                    EvidenceRecord.event_id == event.event_id,
                    EvidenceRecord.task_id == task.external_task_id,
                )
                .first()
            )
            if not existing:
                evidence_type = _infer_evidence_type(event)
                ev = EvidenceRecord(
                    evidence_id=new_id("EVID"),
                    project_id=event.project_id,
                    task_id=task.external_task_id,
                    event_id=event.event_id,
                    evidence_type=evidence_type,
                    source=event.source,
                    timestamp=event.timestamp,
                    confidence=confidence,
                    summary=f"{evidence_type}: {event.title}",
                    metadata_json=metadata_to_json({
                        "link_reason": reason,
                        "agent_id": event.agent_id,
                        "user_id": event.user_id,
                        "original_event_type": event.event_type,
                    }),
                )
                db.add(ev)
                created_evidence.append(ev)

    if created_evidence:
        db.commit()

    return created_evidence


def _infer_evidence_type(event: ProjectEventRecord) -> str:
    et = event.event_type
    if et == EventType.GIT_COMMIT.value:
        return "GIT_COMMIT"
    if et in (EventType.FILE_MODIFIED.value, EventType.FILE_CREATED.value):
        return "FILE_MODIFICATION"
    if et == EventType.BUILD_SUCCEEDED.value:
        return "BUILD_SUCCESS"
    if et == EventType.BUILD_FAILED.value:
        return "BUILD_FAILURE"
    if et == EventType.TEST_FAILED.value:
        return "TEST_FAILURE"
    if et in (EventType.TEST_COMPLETED.value, EventType.TEST_PASSED.value):
        return "TEST_EXECUTION"
    if et == EventType.BUG_REPORTED.value:
        return "QA_DEFECT"
    if et == EventType.BUG_VERIFIED.value:
        return "QA_VERIFICATION"
    if et == EventType.QA_APPROVED.value:
        return "QA_APPROVAL"
    if et == EventType.QA_REJECTED.value:
        return "QA_REJECTION"
    return "ENGINEERING_ACTIVITY"


def backfill_evidence_links(db: Session, project_id: str = "DLX") -> int:
    """Scan existing events and retroactively populate EvidenceRecord rows."""
    events = (
        db.query(ProjectEventRecord)
        .filter(ProjectEventRecord.project_id == project_id)
        .all()
    )
    total_linked = 0
    for e in events:
        linked = link_event_to_tasks(db, e)
        total_linked += len(linked)
    return total_linked


def get_task_evidence_detail(db: Session, task_id: str) -> TaskEvidenceDetailResponse | None:
    """Fetch complete Planned vs Actual evidence breakdown for a single task."""
    task = (
        db.query(TaskRecord)
        .filter((TaskRecord.external_task_id == task_id) | (TaskRecord.id == task_id))
        .first()
    )
    if not task:
        return None

    # Fetch all linked evidence records
    evidence_rows = (
        db.query(EvidenceRecord)
        .filter(EvidenceRecord.task_id == task.external_task_id)
        .order_by(EvidenceRecord.timestamp.desc())
        .all()
    )

    # If no evidence rows yet, run retroactive linker
    if not evidence_rows:
        backfill_evidence_links(db, task.project_id)
        evidence_rows = (
            db.query(EvidenceRecord)
            .filter(EvidenceRecord.task_id == task.external_task_id)
            .order_by(EvidenceRecord.timestamp.desc())
            .all()
        )

    # Compute actual counts
    commits_count = sum(1 for e in evidence_rows if e.evidence_type == "GIT_COMMIT")
    file_mods_count = sum(1 for e in evidence_rows if e.evidence_type == "FILE_MODIFICATION")
    build_successes = sum(1 for e in evidence_rows if e.evidence_type == "BUILD_SUCCESS")
    build_failures = sum(1 for e in evidence_rows if e.evidence_type == "BUILD_FAILURE")
    total_builds = build_successes + build_failures
    test_runs = sum(1 for e in evidence_rows if e.evidence_type in ("TEST_EXECUTION", "TEST_FAILURE"))
    test_failures = sum(1 for e in evidence_rows if e.evidence_type == "TEST_FAILURE")

    # Linked open defects
    defects = (
        db.query(DefectRecord)
        .filter(DefectRecord.related_task_id == task.external_task_id)
        .all()
    )
    open_defects = sum(1 for d in defects if d.status in ("OPEN", "REOPENED"))

    # Determine Plan vs Reality status
    dev_status = "ACTIVE" if (commits_count > 0 or file_mods_count > 0) else ("STALLED" if task.status == "IN_PROGRESS" else "INACTIVE")
    test_status = "FAILING" if test_failures > 0 else ("HEALTHY" if test_runs > 0 else "NO TESTS")
    qa_status = "BLOCKED" if open_defects > 0 else ("APPROVED" if any(e.evidence_type == "QA_APPROVAL" for e in evidence_rows) else "CLEAR")

    if open_defects > 0 or test_failures > 0 or build_failures > 1:
        overall_status = "CRITICAL"
        verdict = "Implementation active, but test regressions and QA defects indicate unresolved risk."
    elif dev_status == "STALLED":
        overall_status = "AT RISK"
        verdict = "Task is marked In Progress in PM tool, but shows no underlying development commits."
    else:
        overall_status = "HEALTHY"
        verdict = "Task telemetry matches project plan."

    # Parse dependencies
    dependencies = []
    try:
        dependencies = json.loads(task.dependencies) if task.dependencies else []
    except Exception:
        dependencies = []

    # Parse labels
    labels = []
    try:
        labels = json.loads(task.labels) if task.labels else []
    except Exception:
        labels = []

    planned_info = {
        "priority": task.priority,
        "sprint": task.sprint or "Sprint 1",
        "due_date": task.due_date or "Not specified",
        "assignee": task.assignee or "Unassigned",
        "reporter": task.reporter or "PM Lead",
        "dependencies": dependencies,
        "labels": labels,
    }

    actual_counts = {
        "commits": commits_count,
        "files_modified": file_mods_count,
        "builds": total_builds,
        "successful_builds": build_successes,
        "failed_builds": build_failures,
        "test_runs": test_runs,
        "failed_tests": test_failures,
        "open_defects": open_defects,
    }

    plan_vs_reality = {
        "development_status": dev_status,
        "testing_status": test_status,
        "qa_status": qa_status,
        "overall_status": overall_status,
        "verdict": verdict,
    }

    evidence_responses = []
    for ev in evidence_rows:
        evidence_responses.append(
            EvidenceResponse(
                id=ev.id,
                evidence_id=ev.evidence_id,
                project_id=ev.project_id,
                task_id=ev.task_id,
                event_id=ev.event_id,
                evidence_type=ev.evidence_type,
                source=ev.source,
                timestamp=ev.timestamp,
                confidence=ev.confidence,
                summary=ev.summary,
                metadata=metadata_from_json(ev.metadata_json),
            )
        )

    return TaskEvidenceDetailResponse(
        task=TaskResponse.model_validate(task),
        planned=planned_info,
        actual_counts=actual_counts,
        plan_vs_reality=plan_vs_reality,
        evidence=evidence_responses,
    )
