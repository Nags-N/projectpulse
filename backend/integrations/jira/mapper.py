"""Data transformation and normalization helpers for Jira Cloud REST API data."""

from datetime import datetime
import json
import logging
from typing import Any

from backend.integrations.jira.schemas import JiraCommentItem, JiraIssueItem
from shared.schemas import UnifiedTask
from shared.timeutil import utc_now, utc_now_naive

logger = logging.getLogger(__name__)


def extract_adf_text(node: Any) -> str:
    """Recursively extract readable plain text from Atlassian Document Format (ADF) JSON structure."""
    if not node:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, (int, float, bool)):
        return str(node)
    if isinstance(node, dict):
        node_type = node.get("type")
        if node_type == "text":
            return node.get("text", "")
        if node_type == "hardBreak":
            return "\n"
        if node_type == "mention":
            attrs = node.get("attrs", {})
            return f"@{attrs.get('text', attrs.get('id', 'user'))}"
        if node_type == "inlineCard":
            return node.get("attrs", {}).get("url", "")
        
        content = node.get("content", [])
        extracted = [extract_adf_text(c) for c in content]
        if node_type in ("paragraph", "heading"):
            joined = "".join(extracted).strip()
            return (joined + "\n") if joined else ""
        elif node_type == "listItem":
            joined = " ".join(filter(None, [e.strip() for e in extracted]))
            return ("• " + joined + "\n") if joined else ""
        elif node_type == "codeBlock":
            joined = "".join(extracted).strip()
            return f"\n```\n{joined}\n```\n"
        return " ".join(filter(None, extracted))
    if isinstance(node, list):
        return "".join(filter(None, (extract_adf_text(item) for item in node)))
    return str(node)


def normalize_jira_status(status_val: Any) -> str:
    """Map Jira status category or name into standardized ProjectPulse status:
    TODO, IN_PROGRESS, BLOCKED, COMPLETED.
    """
    if not status_val:
        return "TODO"
    
    name = ""
    category_key = ""
    if isinstance(status_val, dict):
        name = str(status_val.get("name", "")).strip().upper()
        cat = status_val.get("statusCategory")
        if isinstance(cat, dict):
            category_key = str(cat.get("key", "")).strip().lower()
    else:
        name = str(status_val).strip().upper()

    # Category checks first
    if category_key == "done":
        return "COMPLETED"
    if category_key == "new":
        return "TODO"

    # Name-based checks
    if any(k in name for k in ("DONE", "RESOLVED", "CLOSED", "COMPLETE", "VERIFIED", "SHIPPED", "RELEASED")):
        return "COMPLETED"
    if any(k in name for k in ("BLOCKED", "HOLD", "IMPEDIMENT", "STALLED", "WAITING")):
        return "BLOCKED"
    if any(k in name for k in ("PROGRESS", "DEVELOPMENT", "REVIEW", "TESTING", "QA", "ACTIVE", "WIP")):
        return "IN_PROGRESS"
    
    return "TODO"


def normalize_jira_priority(priority_val: Any) -> str:
    """Map Jira priority into standardized ProjectPulse priority:
    LOW, MEDIUM, HIGH, URGENT.
    """
    if not priority_val:
        return "MEDIUM"
    
    name = ""
    if isinstance(priority_val, dict):
        name = str(priority_val.get("name", "")).strip().upper()
    else:
        name = str(priority_val).strip().upper()

    if any(k in name for k in ("HIGHEST", "BLOCKER", "URGENT", "P0", "CRITICAL")):
        return "URGENT"
    if any(k in name for k in ("HIGH", "P1", "MAJOR")):
        return "HIGH"
    if any(k in name for k in ("LOW", "LOWEST", "TRIVIAL", "MINOR", "P3", "P4")):
        return "LOW"
    return "MEDIUM"


def parse_jira_iso_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        # Jira format: '2026-09-24T12:00:00.000+0000' or with Z
        clean = date_str.replace("Z", "+00:00")
        if "+" in clean and len(clean.split("+")[1]) == 4:
            # Fix +0000 to +00:00
            parts = clean.split("+")
            clean = f"{parts[0]}+{parts[1][:2]}:{parts[1][2:]}"
        return datetime.fromisoformat(clean).replace(tzinfo=None)
    except Exception:
        return None


def jira_issue_to_schema(issue: dict[str, Any], base_url: str) -> JiraIssueItem:
    fields = issue.get("fields", {})
    key = issue.get("key", "")
    summary = fields.get("summary") or f"Issue {key}"
    desc_raw = fields.get("description")
    description = extract_adf_text(desc_raw)

    status_obj = fields.get("status") or {}
    status_str = normalize_jira_status(status_obj)

    priority_obj = fields.get("priority") or {}
    priority_str = normalize_jira_priority(priority_obj)

    issue_type_obj = fields.get("issuetype") or {}
    issue_type_str = issue_type_obj.get("name", "Task") if isinstance(issue_type_obj, dict) else "Task"

    assignee_obj = fields.get("assignee") or {}
    assignee_name = assignee_obj.get("displayName", "") if isinstance(assignee_obj, dict) else ""
    assignee_avatar = ""
    if isinstance(assignee_obj, dict) and "avatarUrls" in assignee_obj:
        assignee_avatar = assignee_obj.get("avatarUrls", {}).get("48x48", "")

    reporter_obj = fields.get("reporter") or {}
    reporter_name = reporter_obj.get("displayName", "") if isinstance(reporter_obj, dict) else ""

    due_date = fields.get("duedate")
    created_at = fields.get("created", "")
    updated_at = fields.get("updated", "")

    # Components
    components_raw = fields.get("components") or []
    components = [c.get("name") for c in components_raw if isinstance(c, dict) and c.get("name")]

    # Labels
    labels = fields.get("labels") or []

    # Story points (check common Jira custom fields or standard name)
    story_points = fields.get("customfield_10016") or fields.get("story_points")
    if story_points is not None:
        try:
            story_points = float(story_points)
        except (ValueError, TypeError):
            story_points = None

    # Parent
    parent_obj = fields.get("parent") or {}
    parent_key = parent_obj.get("key", "") if isinstance(parent_obj, dict) else ""

    # Jira direct URL
    clean_base = base_url.rstrip("/")
    jira_url = f"{clean_base}/browse/{key}" if clean_base and key else ""

    return JiraIssueItem(
        key=key,
        id=str(issue.get("id", "")),
        summary=summary,
        description=description,
        status=status_str,
        priority=priority_str,
        issue_type=issue_type_str,
        assignee=assignee_name,
        assignee_avatar=assignee_avatar,
        reporter=reporter_name,
        created_at=created_at,
        updated_at=updated_at,
        due_date=due_date,
        components=components,
        labels=labels,
        story_points=story_points,
        parent_key=parent_key,
        jira_url=jira_url,
    )


def jira_comment_to_schema(comment: dict[str, Any]) -> JiraCommentItem:
    author_obj = comment.get("author") or {}
    author_name = author_obj.get("displayName", "Jira User") if isinstance(author_obj, dict) else "Jira User"
    body_raw = comment.get("body")
    body_text = extract_adf_text(body_raw)
    return JiraCommentItem(
        id=str(comment.get("id", "")),
        author=author_name,
        body=body_text,
        created_at=str(comment.get("created", "")),
        updated_at=str(comment.get("updated", "")),
    )


def jira_issue_to_unified_task(issue: dict[str, Any], base_url: str, project_id: str) -> UnifiedTask:
    item = jira_issue_to_schema(issue, base_url)
    created_dt = parse_jira_iso_date(item.created_at) or utc_now_naive()
    updated_dt = parse_jira_iso_date(item.updated_at) or utc_now_naive()

    return UnifiedTask(
        project_id=project_id,
        source="JIRA",
        external_task_id=item.key,
        title=item.summary,
        description=item.description,
        status=item.status,
        priority=item.priority,
        assignee=item.assignee,
        reporter=item.reporter,
        due_date=item.due_date,
        sprint="Sprint 1",
        labels=item.labels,
        components=item.components,
        dependencies=[],
        issue_type=item.issue_type,
        story_points=item.story_points,
        parent_key=item.parent_key,
        jira_url=item.jira_url,
        created_at=created_dt,
        updated_at=updated_dt,
    )


def jira_issue_to_task_dict(issue: dict[str, Any], base_url: str, project_id: str) -> dict[str, Any]:
    item = jira_issue_to_schema(issue, base_url)
    created_dt = parse_jira_iso_date(item.created_at) or utc_now_naive()
    updated_dt = parse_jira_iso_date(item.updated_at) or utc_now_naive()

    return {
        "project_id": project_id,
        "source": "JIRA",
        "external_task_id": item.key,
        "title": item.summary,
        "description": item.description,
        "status": item.status,
        "priority": item.priority,
        "assignee": item.assignee,
        "reporter": item.reporter,
        "due_date": item.due_date,
        "sprint": "Sprint 1",
        "dependencies": "[]",
        "labels": json.dumps(item.labels),
        "components": json.dumps(item.components),
        "jira_url": item.jira_url,
        "issue_type": item.issue_type,
        "story_points": item.story_points,
        "parent_key": item.parent_key,
        "created_at": created_dt,
        "updated_at": updated_dt,
    }
