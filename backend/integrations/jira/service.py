"""Jira Cloud Integration Service — orchestrates real API synchronization and persistence."""

from datetime import datetime
import json
import logging
import time
from typing import Any
from sqlalchemy.orm import Session

from backend.config import settings
from backend.integrations.jira.client import JiraCloudClient, JiraClientError
from backend.integrations.jira.mapper import (
    jira_comment_to_schema,
    jira_issue_to_schema,
    jira_issue_to_task_dict,
    jira_issue_to_unified_task,
)
from backend.integrations.jira.schemas import (
    JiraIssueDetailResponse,
    JiraIssueItem,
    JiraSyncStatsResponse,
    JiraTestConnectionResponse,
)
from backend.models.db_models import JiraConnectionRecord, Project, ProjectEventRecord, SyncRunRecord, TaskRecord, User
from backend.services.evidence_service import backfill_evidence_links
from shared.event_types import EventSource, EventType
from shared.timeutil import utc_now_naive

logger = logging.getLogger(__name__)


def _ensure_project(session: Session, project_id: str, client: JiraCloudClient) -> None:
    project = session.get(Project, project_id)
    if not project:
        p_name = f"Jira Project {project_id}"
        p_desc = f"Jira Cloud Project {project_id}"
        if getattr(client, "is_configured", False) and not isinstance(client.is_configured, type(lambda: None)):
            try:
                p_data = client.get_project(project_id)
                if isinstance(p_data, dict):
                    name_val = p_data.get("name")
                    desc_val = p_data.get("description")
                    if isinstance(name_val, str) and name_val:
                        p_name = name_val
                    if isinstance(desc_val, str) and desc_val:
                        p_desc = desc_val
            except Exception:
                pass
        owner_id = _ensure_user(session, "DEV-001", "Alex Rivera (Senior Dev)")
        project = Project(
            project_id=str(project_id),
            name=str(p_name),
            description=str(p_desc),
            folder_path=str(settings.data_dir),
            owner_user_id=str(owner_id),
        )
        session.add(project)
        session.flush()


def _ensure_user(session: Session, user_id: str | None, display_name: str | None = None) -> str:
    uid = str(user_id or "DEV-001").strip()
    if not uid:
        uid = "DEV-001"
    user = session.get(User, uid)
    if not user:
        dev_user = session.get(User, "DEV-001")
        if dev_user:
            return "DEV-001"
        user = User(user_id=str(uid), name=str(display_name or uid), role="DEVELOPER")
        session.add(user)
        session.flush()
    return uid


class JiraService:
    """Service layer managing live Jira Cloud API operations, synchronization, and event recording."""

    def __init__(self, db: Session | None = None, client: JiraCloudClient | None = None):
        self.db = db
        self.client = client or JiraCloudClient()

    def _get_connection_record(self) -> JiraConnectionRecord | None:
        if not self.db:
            return None
        return self.db.query(JiraConnectionRecord).order_by(JiraConnectionRecord.id.desc()).first()

    def _record_connection_status(self, is_success: bool, error_msg: str | None = None, account_email: str | None = None) -> None:
        if not self.db:
            return
        rec = self._get_connection_record()
        now = utc_now_naive()
        if not rec:
            rec = JiraConnectionRecord(
                base_url=self.client.base_url,
                email=account_email or self.client.email,
                project_key=settings.jira_project_key or "DLX",
                status="CONNECTED" if is_success else "ERROR",
                last_tested_at=now,
                error_message=error_msg,
            )
            self.db.add(rec)
        else:
            rec.base_url = self.client.base_url
            rec.email = account_email or self.client.email
            rec.project_key = settings.jira_project_key or rec.project_key
            rec.status = "CONNECTED" if is_success else "ERROR"
            rec.last_tested_at = now
            rec.error_message = error_msg
        try:
            self.db.commit()
        except Exception as exc:
            logger.warning("Failed to persist Jira connection status: %s", exc)
            self.db.rollback()

    def test_connection(self, project_key: str | None = None) -> JiraTestConnectionResponse:
        """Verify Jira credentials and project connectivity against Jira Cloud REST API."""
        proj_key = project_key or settings.jira_project_key or "DLX"
        resp = self.client.test_connection(project_key=proj_key)
        self._record_connection_status(resp.success, resp.error_message, resp.email)
        return resp

    def get_project(self, project_key: str | None = None) -> dict[str, Any]:
        """Fetch project details from Jira Cloud."""
        proj_key = (project_key or settings.jira_project_key or "DLX").strip().upper()
        return self.client.get_project(proj_key)

    def get_issues(
        self,
        project_key: str | None = None,
        limit: int = 50,
        offset: int = 0,
        jql: str | None = None,
    ) -> list[JiraIssueItem]:
        """Fetch issues live from Jira Cloud REST API if configured, otherwise from DB."""
        proj_key = (project_key or settings.jira_project_key or "DLX").strip().upper()

        if self.client.is_configured:
            try:
                res = self.client.search_issues(project_key=proj_key, jql=jql, start_at=offset, max_results=limit)
                raw_issues = res.get("issues", [])
                return [jira_issue_to_schema(i, self.client.base_url) for i in raw_issues]
            except Exception as exc:
                logger.warning("Live Jira search failed, falling back to database: %s", exc)

        # Fallback to DB
        if self.db:
            db_tasks = (
                self.db.query(TaskRecord)
                .filter(TaskRecord.project_id == proj_key, TaskRecord.source == "JIRA")
                .offset(offset)
                .limit(limit)
                .all()
            )
            items = []
            for t in db_tasks:
                try:
                    labels_list = json.loads(t.labels) if t.labels else []
                except Exception:
                    labels_list = []
                try:
                    comp_list = json.loads(t.components) if t.components else []
                except Exception:
                    comp_list = []
                items.append(JiraIssueItem(
                    key=t.external_task_id,
                    id=str(t.id),
                    summary=t.title,
                    description=t.description or "",
                    status=t.status,
                    priority=t.priority,
                    issue_type=t.issue_type,
                    assignee=t.assignee or "",
                    reporter=t.reporter or "",
                    created_at=t.created_at.isoformat() if t.created_at else "",
                    updated_at=t.updated_at.isoformat() if t.updated_at else "",
                    due_date=t.due_date,
                    components=comp_list,
                    labels=labels_list,
                    story_points=t.story_points,
                    parent_key=t.parent_key or "",
                    jira_url=t.jira_url or (f"{self.client.base_url}/browse/{t.external_task_id}" if self.client.base_url else ""),
                ))
            return items

        return []

    def get_issue_detail(self, issue_key: str) -> JiraIssueDetailResponse:
        """Fetch issue details and live comments from Jira Cloud REST API."""
        if not self.client.is_configured:
            raise JiraClientError("Jira credentials are not configured", 401)

        raw_issue = self.client.get_issue(issue_key)
        issue_item = jira_issue_to_schema(raw_issue, self.client.base_url)

        try:
            raw_comments = self.client.get_comments(issue_key)
            comment_items = [jira_comment_to_schema(c) for c in raw_comments]
        except Exception as exc:
            logger.warning("Could not fetch comments for Jira issue %s: %s", issue_key, exc)
            comment_items = []

        return JiraIssueDetailResponse(issue=issue_item, comments=comment_items)

    def sync_project(self, project_key: str | None = None, db: Session | None = None) -> JiraSyncStatsResponse:
        """Execute real synchronization from Jira Cloud REST API into TaskRecord database."""
        session = db or self.db
        if not session:
            raise ValueError("Database session required for Jira synchronization")

        proj_key = (project_key or settings.jira_project_key or "KAN").strip().upper()
        if not self.client.is_configured:
            return JiraSyncStatsResponse(
                status="FAILED",
                success=False,
                project_key=proj_key,
                error_message="Jira credentials are not configured. Set JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN in .env.",
            )

        _ensure_project(session, proj_key, self.client)

        start_time = time.time()
        start_dt = utc_now_naive()
        sync_run = SyncRunRecord(
            integration_id=f"SYNC-JIRA-{int(start_dt.timestamp())}",
            source="JIRA",
            project_id=proj_key,
            sync_started=start_dt,
            status="IN_PROGRESS",
        )
        session.add(sync_run)
        session.commit()

        records_fetched = 0
        records_created = 0
        records_updated = 0
        records_unchanged = 0
        records_failed = 0
        error_msg = None

        try:
            raw_issues = self.client.fetch_all_issues(project_key=proj_key, max_total=500)
            records_fetched = len(raw_issues)

            for issue in raw_issues:
                try:
                    task_data = jira_issue_to_task_dict(issue, self.client.base_url, proj_key)
                    key = task_data["external_task_id"]

                    existing = (
                        session.query(TaskRecord)
                        .filter(
                            TaskRecord.project_id == proj_key,
                            TaskRecord.external_task_id == key,
                        )
                        .first()
                    )

                    if not existing:
                        new_task = TaskRecord(
                            project_id=proj_key,
                            source="JIRA",
                            external_task_id=key,
                            title=task_data["title"],
                            description=task_data["description"],
                            status=task_data["status"],
                            priority=task_data["priority"],
                            assignee=task_data["assignee"],
                            reporter=task_data["reporter"],
                            due_date=task_data["due_date"],
                            sprint=task_data["sprint"],
                            dependencies=task_data["dependencies"],
                            labels=task_data["labels"],
                            components=task_data["components"],
                            jira_url=task_data["jira_url"],
                            issue_type=task_data["issue_type"],
                            story_points=task_data["story_points"],
                            parent_key=task_data["parent_key"],
                            last_synced_at=start_dt,
                            created_at=task_data["created_at"],
                            updated_at=task_data["updated_at"],
                        )
                        session.add(new_task)
                        records_created += 1

                        # Ingest timeline event for new Jira task
                        reporter_user = _ensure_user(session, task_data.get("reporter"), task_data.get("reporter"))
                        session.add(ProjectEventRecord(
                            event_id=f"EVT-JIRA-{key}-{int(time.time()*1000)}",
                            source=EventSource.JIRA.value,
                            event_type=EventType.TASK_CREATED.value,
                            project_id=proj_key,
                            user_id=reporter_user,
                            agent_id="AGENT-JIRA-SYNC",
                            role="DEVELOPER",
                            status="INFO",
                            timestamp=start_dt,
                            title=f"Jira Issue Synced: {key}",
                            description=f"Created [{key}] {task_data['title']} (Type: {task_data['issue_type']}, Status: {task_data['status']})",
                            metadata_json=json.dumps({"task_id": key, "jira_url": task_data["jira_url"], "priority": task_data["priority"]}),
                            created_at=start_dt,
                        ))
                    else:
                        # Check if anything changed
                        changed = (
                            existing.title != task_data["title"]
                            or (existing.description or "") != (task_data["description"] or "")
                            or existing.status != task_data["status"]
                            or existing.priority != task_data["priority"]
                            or (existing.assignee or "") != (task_data["assignee"] or "")
                            or (existing.reporter or "") != (task_data["reporter"] or "")
                            or existing.due_date != task_data["due_date"]
                            or existing.labels != task_data["labels"]
                            or existing.components != task_data["components"]
                            or existing.issue_type != task_data["issue_type"]
                            or existing.story_points != task_data["story_points"]
                            or existing.jira_url != task_data["jira_url"]
                        )

                        if changed:
                            old_status = existing.status
                            existing.title = task_data["title"]
                            existing.description = task_data["description"]
                            existing.status = task_data["status"]
                            existing.priority = task_data["priority"]
                            existing.assignee = task_data["assignee"]
                            existing.reporter = task_data["reporter"]
                            existing.due_date = task_data["due_date"]
                            existing.labels = task_data["labels"]
                            existing.components = task_data["components"]
                            existing.jira_url = task_data["jira_url"]
                            existing.issue_type = task_data["issue_type"]
                            existing.story_points = task_data["story_points"]
                            existing.parent_key = task_data["parent_key"]
                            existing.last_synced_at = start_dt
                            existing.updated_at = start_dt
                            records_updated += 1

                            # Ingest timeline event for updated Jira task
                            assignee_user = _ensure_user(session, task_data.get("assignee"), task_data.get("assignee"))
                            session.add(ProjectEventRecord(
                                event_id=f"EVT-JIRA-{key}-{int(time.time()*1000)}",
                                source=EventSource.JIRA.value,
                                event_type=EventType.TASK_UPDATED.value,
                                project_id=proj_key,
                                user_id=assignee_user,
                                agent_id="AGENT-JIRA-SYNC",
                                role="DEVELOPER",
                                status="INFO",
                                timestamp=start_dt,
                                title=f"Jira Issue Updated: {key}",
                                description=f"Updated [{key}] status '{old_status}' -> '{task_data['status']}'",
                                metadata_json=json.dumps({"task_id": key, "jira_url": task_data["jira_url"], "status": task_data["status"]}),
                                created_at=start_dt,
                            ))
                        else:
                            existing.last_synced_at = start_dt
                            records_unchanged += 1

                except Exception as item_err:
                    logger.error("Error processing Jira issue: %s", item_err)
                    records_failed += 1

            session.commit()

            # Trigger automated evidence linking against new Jira issues
            try:
                backfill_evidence_links(session, proj_key)
            except Exception as ev_err:
                logger.warning("Auto-linking evidence error after Jira sync: %s", ev_err)

            status_str = "SUCCESS" if records_failed == 0 else "PARTIAL_SUCCESS"

        except Exception as exc:
            logger.error("Jira synchronization failed: %s", exc)
            session.rollback()
            status_str = "FAILED"
            error_msg = str(exc)

        duration = round(time.time() - start_time, 2)
        end_dt = utc_now_naive()

        # Update sync run record
        sync_run.sync_completed = end_dt
        sync_run.records_fetched = records_fetched
        sync_run.records_created = records_created
        sync_run.records_updated = records_updated
        sync_run.records_failed = records_failed
        sync_run.status = status_str
        sync_run.error_message = error_msg or ""
        session.commit()

        # Update Jira Connection status
        conn_rec = self._get_connection_record()
        if conn_rec:
            conn_rec.last_synced_at = end_dt
            conn_rec.status = "CONNECTED" if status_str != "FAILED" else "ERROR"
            if error_msg:
                conn_rec.error_message = error_msg
            session.commit()

        return JiraSyncStatsResponse(
            status=status_str,
            success=(status_str != "FAILED"),
            records_fetched=records_fetched,
            records_created=records_created,
            records_updated=records_updated,
            records_unchanged=records_unchanged,
            records_failed=records_failed,
            project_key=proj_key,
            duration_sec=duration,
            error_message=error_msg,
            synced_at=end_dt.isoformat(),
            last_synced_at=end_dt.isoformat(),
        )

    def handle_webhook(self, payload: dict[str, Any], db: Session) -> dict[str, Any]:
        """Handle incoming Jira Cloud webhooks for real-time issue changes."""
        issue = payload.get("issue")
        event_name = payload.get("webhookEvent", "jira:issue_updated")
        if not issue:
            return {"status": "ignored", "reason": "No issue object in payload"}

        proj_key = issue.get("fields", {}).get("project", {}).get("key") or settings.jira_project_key or "KAN"
        _ensure_project(db, proj_key, self.client)
        task_data = jira_issue_to_task_dict(issue, self.client.base_url, proj_key)
        key = task_data["external_task_id"]
        now = utc_now_naive()

        existing = (
            db.query(TaskRecord)
            .filter(TaskRecord.project_id == proj_key, TaskRecord.external_task_id == key)
            .first()
        )

        if not existing:
            new_task = TaskRecord(
                project_id=proj_key,
                source="JIRA",
                external_task_id=key,
                title=task_data["title"],
                description=task_data["description"],
                status=task_data["status"],
                priority=task_data["priority"],
                assignee=task_data["assignee"],
                reporter=task_data["reporter"],
                due_date=task_data["due_date"],
                sprint=task_data["sprint"],
                dependencies=task_data["dependencies"],
                labels=task_data["labels"],
                components=task_data["components"],
                jira_url=task_data["jira_url"],
                issue_type=task_data["issue_type"],
                story_points=task_data["story_points"],
                parent_key=task_data["parent_key"],
                last_synced_at=now,
                created_at=task_data["created_at"],
                updated_at=now,
            )
            db.add(new_task)
            action = "created"
        else:
            existing.title = task_data["title"]
            existing.description = task_data["description"]
            existing.status = task_data["status"]
            existing.priority = task_data["priority"]
            existing.assignee = task_data["assignee"]
            existing.reporter = task_data["reporter"]
            existing.due_date = task_data["due_date"]
            existing.labels = task_data["labels"]
            existing.components = task_data["components"]
            existing.jira_url = task_data["jira_url"]
            existing.issue_type = task_data["issue_type"]
            existing.story_points = task_data["story_points"]
            existing.parent_key = task_data["parent_key"]
            existing.last_synced_at = now
            existing.updated_at = now
            action = "updated"

        # Record timeline event
        user_name = payload.get("user", {}).get("displayName", "Jira Webhook")
        wh_user = _ensure_user(db, "DEV-001", user_name)
        event_type = EventType.TASK_CREATED.value if action == "created" else EventType.TASK_UPDATED.value
        db.add(ProjectEventRecord(
            event_id=f"EVT-WH-{key}-{int(time.time()*1000)}",
            source=EventSource.JIRA.value,
            event_type=event_type,
            project_id=proj_key,
            user_id=wh_user,
            agent_id="AGENT-JIRA-WEBHOOK",
            role="DEVELOPER",
            status="INFO",
            timestamp=now,
            title=f"Jira Webhook: [{key}] {action.capitalize()}",
            description=f"Issue {key} was {action} via Jira Cloud webhook ({event_name}). Status: {task_data['status']}",
            metadata_json=json.dumps({"task_id": key, "jira_url": task_data["jira_url"], "webhook_event": event_name}),
            created_at=now,
        ))

        db.commit()

        try:
            backfill_evidence_links(db, proj_key)
        except Exception as exc:
            logger.warning("Failed to link evidence on webhook: %s", exc)

        return {"status": "ok", "action": action, "task_id": key}
