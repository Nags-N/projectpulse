"""Synchronization Service — fetches, normalizes, and syncs tasks from PM tools.

Implements Sections 12 & 29:
- Syncs tasks across connected PM adapters (Jira, Trello, Linear, Asana, Monday, ClickUp).
- Logs audit history in SyncRunRecord table (status, records fetched/created/updated/failed, timestamps).
- Automatically triggers evidence linking upon synchronization.
"""

import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from backend.integrations.registry import integration_manager
from backend.models.db_models import SyncRunRecord, TaskRecord
from backend.models.schemas import TaskCreate
from backend.services.evidence_service import backfill_evidence_links
from backend.services.task_service import create_or_update_task
from shared.timeutil import utc_now_naive

logger = logging.getLogger(__name__)


def sync_all_integrations(db: Session, project_id: str = "DLX") -> dict:
    """Sync tasks across all connected PM platforms into the database."""
    total_synced = 0
    synced_platforms = []
    run_records = []

    for item in integration_manager.list_integrations():
        if item["connected"]:
            platform = item["platform"]
            result = sync_single_platform(db, platform=platform, project_id=project_id)
            total_synced += result.get("records_synced", 0)
            synced_platforms.append(platform)
            run_records.append(result)

    # Automatically trigger evidence linking
    try:
        backfill_evidence_links(db, project_id)
    except Exception as exc:
        logger.warning("Could not auto-link evidence post-sync: %s", exc)

    logger.info("Synced %d tasks from platforms: %s", total_synced, synced_platforms)
    return {
        "status": "ok",
        "total_tasks_synced": total_synced,
        "synced_platforms": synced_platforms,
        "runs": run_records,
    }


def sync_single_platform(db: Session, platform: str, project_id: str = "DLX") -> dict:
    """Sync tasks for a single specific PM platform and record audit history."""
    if platform.upper() == "JIRA":
        from backend.integrations.jira.service import JiraService
        service = JiraService(db)
        res = service.sync_project(project_id)
        return {
            "platform": "JIRA",
            "status": res.status,
            "records_fetched": res.records_fetched,
            "records_synced": res.records_created + res.records_updated,
            "records_created": res.records_created,
            "records_updated": res.records_updated,
            "records_unchanged": res.records_unchanged,
            "records_failed": res.records_failed,
            "duration_sec": res.duration_sec,
            "error": res.error_message or "",
        }

    adapter = integration_manager.get_adapter(platform)
    if not adapter:
        return {"status": "error", "message": f"Platform '{platform}' adapter not found"}

    start_time = utc_now_naive()
    sync_run = SyncRunRecord(
        integration_id=f"SYNC-{platform.upper()}-{int(start_time.timestamp())}",
        source=platform.upper(),
        project_id=project_id,
        sync_started=start_time,
        status="IN_PROGRESS",
    )
    db.add(sync_run)
    db.commit()

    records_fetched = 0
    records_created = 0
    records_updated = 0
    records_failed = 0
    error_msg = ""

    try:
        tasks = adapter.get_tasks(project_id)
        records_fetched = len(tasks)

        for t in tasks:
            try:
                # Check if exists before creating
                existing = (
                    db.query(TaskRecord)
                    .filter(
                        TaskRecord.project_id == project_id,
                        TaskRecord.external_task_id == t.external_task_id,
                    )
                    .first()
                )
                deps_json = json.dumps(t.dependencies) if hasattr(t, "dependencies") and t.dependencies else "[]"
                labels_json = json.dumps(t.labels) if hasattr(t, "labels") and t.labels else "[]"
                reporter_val = getattr(t, "reporter", "") or ""
                sprint_val = getattr(t, "sprint", "Sprint 1") or "Sprint 1"
                issue_type_val = getattr(t, "issue_type", "Task") or "Task"
                story_points_val = getattr(t, "story_points", None)
                parent_key_val = getattr(t, "parent_key", "") or ""

                if existing:
                    existing.title = t.title
                    existing.description = t.description
                    existing.status = t.status
                    existing.priority = t.priority
                    existing.assignee = t.assignee
                    existing.due_date = t.due_date
                    existing.reporter = reporter_val or existing.reporter
                    existing.sprint = sprint_val or existing.sprint
                    if hasattr(t, "dependencies") and t.dependencies:
                        existing.dependencies = deps_json
                    if hasattr(t, "labels") and t.labels:
                        existing.labels = labels_json
                    existing.issue_type = issue_type_val
                    if story_points_val is not None:
                        existing.story_points = story_points_val
                    if parent_key_val:
                        existing.parent_key = parent_key_val
                    existing.updated_at = utc_now_naive()
                    records_updated += 1
                else:
                    db_task = TaskRecord(
                        project_id=project_id,
                        source=t.source,
                        external_task_id=t.external_task_id,
                        title=t.title,
                        description=t.description,
                        status=t.status,
                        priority=t.priority,
                        assignee=t.assignee,
                        reporter=reporter_val,
                        due_date=t.due_date,
                        sprint=sprint_val,
                        dependencies=deps_json,
                        labels=labels_json,
                        issue_type=issue_type_val,
                        story_points=story_points_val,
                        parent_key=parent_key_val,
                    )
                    db.add(db_task)
                    records_created += 1
            except Exception as task_err:
                logger.error("Failed to sync task %s: %s", t.external_task_id, task_err)
                records_failed += 1

        db.commit()
        status_val = "SUCCESS" if records_failed == 0 else "PARTIAL_SUCCESS"

    except Exception as exc:
        logger.error("Error during sync of %s: %s", platform, exc)
        status_val = "FAILED"
        error_msg = str(exc)

    end_time = utc_now_naive()
    sync_run.sync_completed = end_time
    sync_run.records_fetched = records_fetched
    sync_run.records_created = records_created
    sync_run.records_updated = records_updated
    sync_run.records_failed = records_failed
    sync_run.status = status_val
    sync_run.error_message = error_msg
    db.commit()

    return {
        "platform": platform,
        "status": status_val,
        "records_fetched": records_fetched,
        "records_synced": records_created + records_updated,
        "records_created": records_created,
        "records_updated": records_updated,
        "records_failed": records_failed,
        "duration_sec": (end_time - start_time).total_seconds(),
        "error": error_msg,
    }


def list_sync_history(db: Session, project_id: str | None = None, limit: int = 50) -> list[SyncRunRecord]:
    """Retrieve audit history of PM synchronization runs."""
    query = db.query(SyncRunRecord)
    if project_id:
        query = query.filter(SyncRunRecord.project_id == project_id)
    return query.order_by(SyncRunRecord.sync_started.desc()).limit(limit).all()
