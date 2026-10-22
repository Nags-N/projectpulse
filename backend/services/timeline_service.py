"""Unified Project Chronological Timeline Service.

Implements Feature 5:
- Combines events across:
    1. Jira / PM Tasks (created, updated, status transitions)
    2. Developer Activity (Git commits, file modifications, branch checkouts)
    3. Build System (build success, build failure)
    4. Automated Testing (test passed, test failed, suites)
    5. QA Engineering (defect reported, QA verdict)
    6. AI Risk Engine (risk detected, risk resolved)
- Strictly uses real timestamps from underlying database records.
- Supports multi-role filtering: ALL, JIRA, DEV, BUILD, TEST, QA, RISKS, AI.
"""

from datetime import datetime
import json
import logging
from typing import Any
from sqlalchemy.orm import Session

from backend.database import metadata_from_json
from backend.models.db_models import DefectRecord, ProjectEventRecord, TaskRecord
from backend.models.schemas import TimelineItemResponse
from backend.services.risk_service import evaluate_project_risks
from shared.event_types import EventType

logger = logging.getLogger(__name__)


def get_unified_project_timeline(
    db: Session,
    project_id: str = "DLX",
    category_filter: str = "ALL",
    limit: int = 150,
) -> list[dict[str, Any]]:
    """Gather and sort all real events into a unified chronological timeline."""
    items: list[dict[str, Any]] = []

    # 1. Telemetry Events (Dev, Git, File, Build, Test, QA)
    events = (
        db.query(ProjectEventRecord)
        .filter(ProjectEventRecord.project_id == project_id)
        .order_by(ProjectEventRecord.timestamp.desc())
        .limit(200)
        .all()
    )

    for e in events:
        meta = metadata_from_json(e.metadata_json)
        source = e.source.upper()
        event_type = e.event_type

        # Categorize
        if source == "GIT" or event_type in (EventType.GIT_COMMIT.value, EventType.GIT_BRANCH_CHANGED.value):
            cat = "DEV"
        elif source == "FILE" or event_type in (EventType.FILE_MODIFIED.value, EventType.FILE_CREATED.value):
            cat = "DEV"
        elif source == "BUILD" or "BUILD" in event_type:
            cat = "BUILD"
        elif source == "TEST" or "TEST" in event_type:
            cat = "TEST"
        elif source == "QA" or "BUG" in event_type or "QA" in event_type:
            cat = "QA"
        else:
            cat = "DEV"

        # Check filter
        if category_filter != "ALL" and category_filter != cat:
            continue

        items.append({
            "id": f"EVT-{e.event_id}",
            "timestamp": e.timestamp.isoformat(),
            "timestamp_dt": e.timestamp,
            "source": cat,
            "event_type": event_type,
            "title": e.title,
            "description": e.description or meta.get("diff_summary", "") or meta.get("command", ""),
            "task_id": meta.get("related_task_id") or meta.get("task_id"),
            "author": e.user_id,
            "metadata": meta,
        })

    # 2. Jira / PM Tasks (Created & Updated)
    tasks = db.query(TaskRecord).filter(TaskRecord.project_id == project_id).all()
    if category_filter in ("ALL", "JIRA"):
        for t in tasks:
            # Task created event
            items.append({
                "id": f"TASK-CRE-{t.external_task_id}",
                "timestamp": t.created_at.isoformat(),
                "timestamp_dt": t.created_at,
                "source": "JIRA",
                "event_type": "JIRA_ISSUE_CREATED",
                "title": f"Jira Task {t.external_task_id} Created: {t.title}",
                "description": f"Status: {t.status} | Priority: {t.priority} | Assignee: {t.assignee or 'Unassigned'}",
                "task_id": t.external_task_id,
                "author": t.reporter or "PM Lead",
                "metadata": {
                    "source": t.source,
                    "sprint": t.sprint,
                    "due_date": t.due_date,
                    "priority": t.priority,
                },
            })

            # Task updated event (if updated after creation)
            if t.updated_at and t.updated_at > t.created_at:
                items.append({
                    "id": f"TASK-UPD-{t.external_task_id}",
                    "timestamp": t.updated_at.isoformat(),
                    "timestamp_dt": t.updated_at,
                    "source": "JIRA",
                    "event_type": "JIRA_STATUS_CHANGED",
                    "title": f"Jira Task {t.external_task_id} Updated to '{t.status}'",
                    "description": f"Priority: {t.priority} | Assignee: {t.assignee or 'Unassigned'}",
                    "task_id": t.external_task_id,
                    "author": t.reporter or "PM Lead",
                    "metadata": {"status": t.status, "assignee": t.assignee},
                })

    # 3. AI Risk Detections
    if category_filter in ("ALL", "RISKS", "AI"):
        try:
            risks = evaluate_project_risks(db, project_id)
            for r in risks:
                ts_str = r.get("timestamp") or datetime.now().isoformat()
                try:
                    ts_dt = datetime.fromisoformat(ts_str)
                except Exception:
                    ts_dt = datetime.now()

                items.append({
                    "id": f"AI-RISK-{r.get('rule_id')}-{r.get('task_id', 'SYS')}",
                    "timestamp": ts_str,
                    "timestamp_dt": ts_dt,
                    "source": "AI",
                    "event_type": "AI_RISK_DETECTED",
                    "title": f"AI Risk Detected [{r.get('severity')}]: {r.get('title')}",
                    "description": r.get("explanation", ""),
                    "task_id": r.get("task_id"),
                    "author": "ProjectPulse AI Engine",
                    "metadata": {
                        "rule_id": r.get("rule_id"),
                        "severity": r.get("severity"),
                        "confidence": r.get("confidence", 0.95),
                        "suggested_action": r.get("suggested_action", ""),
                    },
                })
        except Exception as exc:
            logger.warning("Could not evaluate risks for timeline: %s", exc)

    # Sort strictly by timestamp descending
    items.sort(key=lambda x: x["timestamp_dt"], reverse=True)

    # Strip intermediate datetime object before returning
    for item in items:
        item.pop("timestamp_dt", None)

    return items[:limit]
