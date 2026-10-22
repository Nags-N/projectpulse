"""Pydantic schemas for Jira Cloud REST API v3 integration."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class JiraTestConnectionResponse(BaseModel):
    success: bool
    connected: bool = True
    provider: str = "jira"
    user_display_name: str = ""
    authenticated_user: str = ""
    account_id: str = ""
    email: str = ""
    project_found: bool = False
    project_key: str = ""
    project_name: str = ""
    base_url: str = ""
    error_message: str | None = None


class JiraIssueItem(BaseModel):
    key: str
    id: str = ""
    summary: str
    description: str = ""
    status: str = "TODO"
    priority: str = "MEDIUM"
    issue_type: str = "Task"
    assignee: str = ""
    assignee_avatar: str = ""
    reporter: str = ""
    created_at: str = ""
    updated_at: str = ""
    due_date: str | None = None
    components: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    story_points: float | None = None
    parent_key: str = ""
    jira_url: str = ""


class JiraCommentItem(BaseModel):
    id: str
    author: str = ""
    body: str = ""
    created_at: str = ""
    updated_at: str = ""


class JiraIssueDetailResponse(BaseModel):
    issue: JiraIssueItem
    comments: list[JiraCommentItem] = Field(default_factory=list)


class JiraSyncStatsResponse(BaseModel):
    status: str
    success: bool = True
    records_fetched: int = 0
    records_created: int = 0
    records_updated: int = 0
    records_unchanged: int = 0
    records_failed: int = 0
    project_key: str = ""
    duration_sec: float = 0.0
    error_message: str | None = None
    synced_at: str = ""
    last_synced_at: str = ""


class JiraWebhookPayload(BaseModel):
    webhookEvent: str = ""
    timestamp: int | None = None
    issue: dict[str, Any] | None = None
    changelog: dict[str, Any] | None = None
    user: dict[str, Any] | None = None
