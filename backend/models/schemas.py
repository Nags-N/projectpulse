"""Pydantic API schemas for ProjectPulse AI."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_serializer

from shared.event_types import EventSource, EventType, UserRole
from shared.events import ProjectEvent, ProjectEventCreate
from shared.timeutil import to_iso_utc, utc_now


def new_id(prefix: str = "") -> str:
    uid = uuid4().hex[:8].upper()
    return f"{prefix}-{uid}" if prefix else str(uuid4())


class UserCreate(BaseModel):
    user_id: str | None = None
    name: str
    role: UserRole = UserRole.DEVELOPER
    external_id: str | None = None


class UserResponse(BaseModel):
    user_id: str
    name: str
    role: str
    external_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectCreate(BaseModel):
    project_id: str | None = None
    name: str
    folder_path: str
    description: str = ""
    owner_user_id: str


class ProjectResponse(BaseModel):
    project_id: str
    name: str
    folder_path: str
    description: str = ""
    owner_user_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Agent Schemas
class AgentRegisterRequest(BaseModel):
    agent_id: str
    user_id: str
    project_id: str
    role: UserRole = UserRole.DEVELOPER
    machine_name: str = "LOCAL-PC"
    machine_id: str = "LOCAL-MACHINE"


class AgentHeartbeatRequest(BaseModel):
    agent_id: str
    monitoring_active: bool = True
    timestamp: datetime = Field(default_factory=utc_now)


class AgentResponse(BaseModel):
    agent_id: str
    user_id: str
    project_id: str
    role: str
    machine_name: str
    machine_id: str
    status: str
    last_seen: datetime
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("last_seen", "created_at")
    def _serialize_dates(self, value: datetime | None) -> str | None:
        return to_iso_utc(value)


# Event Schemas
class EventIngestRequest(ProjectEventCreate):
    pass


class EventResponse(ProjectEvent):
    created_at: datetime | None = None
    human_description: str = ""
    display_title: str = ""

    model_config = {"from_attributes": True}

    @field_serializer("created_at")
    def _serialize_created_at(self, value: datetime | None) -> str | None:
        return to_iso_utc(value)


# Task Schemas
class TaskCreate(BaseModel):
    project_id: str
    source: str = "MANUAL"
    external_task_id: str
    title: str
    description: str = ""
    status: str = "TODO"
    priority: str = "MEDIUM"
    assignee: str = ""
    reporter: str = ""
    due_date: str | None = None
    sprint: str = "Sprint 1"
    dependencies: str = "[]"
    labels: str = "[]"
    components: str = "[]"
    jira_url: str = ""
    issue_type: str = "Task"
    story_points: float | None = None
    parent_key: str = ""


class TaskResponse(BaseModel):
    id: int
    project_id: str
    source: str
    external_task_id: str
    title: str
    description: str
    status: str
    priority: str
    assignee: str
    reporter: str = ""
    due_date: str | None
    sprint: str = "Sprint 1"
    dependencies: str = "[]"
    labels: str = "[]"
    components: str = "[]"
    jira_url: str = ""
    issue_type: str = "Task"
    story_points: float | None = None
    parent_key: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EvidenceResponse(BaseModel):
    id: int
    evidence_id: str
    project_id: str
    task_id: str
    event_id: str
    evidence_type: str
    source: str
    timestamp: datetime
    confidence: float = 1.0
    summary: str = ""
    metadata: dict = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class TaskEvidenceDetailResponse(BaseModel):
    task: TaskResponse
    planned: dict
    actual_counts: dict
    plan_vs_reality: dict
    evidence: list[EvidenceResponse] = Field(default_factory=list)


class SyncRunResponse(BaseModel):
    id: int
    integration_id: str
    source: str
    project_id: str
    sync_started: datetime
    sync_completed: datetime | None = None
    records_fetched: int = 0
    records_created: int = 0
    records_updated: int = 0
    records_failed: int = 0
    status: str = "SUCCESS"
    error_message: str = ""

    model_config = {"from_attributes": True}


# Summaries & Dashboards
class ActivitySummary(BaseModel):
    total_activities: int = 0
    commits: int = 0
    build_failures: int = 0
    build_successes: int = 0
    file_modifications: int = 0
    files_created: int = 0
    branch_changes: int = 0
    test_runs: int = 0
    test_failures: int = 0
    bugs_reported: int = 0


class DeveloperSummaryResponse(BaseModel):
    project_id: str
    project_name: str
    date: str
    activity: ActivitySummary
    highlights: list[str] = Field(default_factory=list)
    recent_events: list[EventResponse] = Field(default_factory=list)
    current_status: str = "No activity recorded"
    narrative_summary: str = ""
    what_you_did: list[str] = Field(default_factory=list)
    monitoring_active: bool = True
    display_timezone: str = "Asia/Kolkata"


class HealthScorecard(BaseModel):
    overall_status: str = "ATTENTION_REQUIRED"  # HEALTHY, ATTENTION_REQUIRED, CRITICAL
    tasks_status: str = "Healthy"
    development_status: str = "Healthy"
    testing_status: str = "Healthy"
    qa_status: str = "Healthy"
    dependencies_status: str = "No blockers"


class ManagerDashboardResponse(BaseModel):
    project_id: str
    project_name: str
    activity: ActivitySummary
    recent_events: list[EventResponse] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)
    narrative_summary: str = ""
    health: HealthScorecard = Field(default_factory=HealthScorecard)
    team_agents: list[AgentResponse] = Field(default_factory=list)
    tasks_summary: dict = Field(default_factory=dict)
    active_risks: list[dict] = Field(default_factory=list)



class AppConfigResponse(BaseModel):
    project_id: str
    user_id: str
    project_name: str
    backend_url: str = "http://127.0.0.1:8000"
    frontend_url: str = "http://127.0.0.1:5173"
    monitoring_active: bool = True


class MonitoringStatusUpdate(BaseModel):
    active: bool
    project_id: str | None = None


# QA & Defect Schemas
class DefectCreate(BaseModel):
    title: str
    description: str = ""
    severity: str = "HIGH"  # LOW, MEDIUM, HIGH, CRITICAL
    priority: str = "HIGH"  # LOW, MEDIUM, HIGH, URGENT
    related_task_id: str = ""
    reported_by: str = "QA"


class DefectStatusUpdate(BaseModel):
    status: str  # OPEN, VERIFIED, CLOSED, REOPENED


class VerdictCreate(BaseModel):
    approved: bool
    build_ref: str = "main"
    notes: str = ""


# AI Assistant Schemas (Phases 14 & 15)
class AIChatRequest(BaseModel):
    query: str


class AIChatResponse(BaseModel):
    query: str
    answer: str
    citations: list[str] = Field(default_factory=list)
    retrieved_context: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = ""


# Real Jira Schemas
class JiraConnectRequest(BaseModel):
    base_url: str
    email: str
    api_token: str
    project_key: str = ""


class JiraProjectResponse(BaseModel):
    id: str
    key: str
    name: str
    lead: str = ""


class JiraSyncRequest(BaseModel):
    project_id: str = "DLX"
    jira_project_key: str = ""


# AI Risk Detection Schemas
class AIRiskItem(BaseModel):
    risk_id: str = ""
    rule_id: str
    risk_type: str
    severity: str
    category: str = "QUALITY"
    title: str
    task_id: str = ""
    task_title: str = ""
    facts: list[str] = Field(default_factory=list)
    explanation: str
    confidence: float = 1.0
    suggested_action: str = ""
    timestamp: str = ""


# AI Summary Schemas
class AISummaryRequest(BaseModel):
    summary_type: str = "project"  # project, task, developer, risk, timeline
    timeframe: str = "24h"
    user_id: str | None = None


class AISummaryResponse(BaseModel):
    project_id: str
    summary_type: str
    title: str
    summary: str
    key_findings: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    generated_at: str = ""


# Unified Project Timeline Schemas
class TimelineItemResponse(BaseModel):
    id: str
    timestamp: str
    source: str
    event_type: str
    title: str
    description: str = ""
    task_id: str | None = None
    author: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


# Code Change Explanation Schemas
class CodeExplanationResponse(BaseModel):
    explanation_id: str
    event_id: str
    timestamp: str
    commit_hash: str = ""
    commit_message: str = ""
    author: str = ""
    files_changed_count: int = 0
    files_changed: list[str] = Field(default_factory=list)
    inferred_module: str = ""
    matched_task_id: str = ""
    matched_task_title: str = ""
    confidence_level: str = "LIKELY"  # DIRECT, LIKELY, PLAUSIBLE, UNLINKED
    confidence_score: float = 0.85
    explanation: str = ""
    evidence_signals: list[str] = Field(default_factory=list)


