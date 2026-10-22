"""Shared unified schemas across agents, adapters, and backend."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

from shared.event_types import EventSource, EventType, UserRole
from shared.events import ProjectEvent, ProjectEventCreate
from shared.timeutil import utc_now


class UnifiedTask(BaseModel):
    """Normalized task model representing tasks from Jira, Trello, Asana, Linear, etc."""

    task_id: str | None = None
    project_id: str
    source: str = "MANUAL"
    external_task_id: str
    title: str
    description: str = ""
    status: str = "TODO"  # TODO, IN_PROGRESS, BLOCKED, COMPLETED
    priority: str = "MEDIUM"  # LOW, MEDIUM, HIGH, URGENT
    assignee: str = ""
    reporter: str = ""
    due_date: str | None = None
    sprint: str = "Sprint 1"
    labels: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    issue_type: str = "Task"
    story_points: float | None = None
    parent_key: str = ""
    jira_url: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AgentRegistration(BaseModel):
    """Payload sent by an agent when registering with the backend."""

    agent_id: str
    user_id: str
    project_id: str
    role: UserRole
    machine_name: str = "LOCAL-PC"
    machine_id: str = "LOCAL-MACHINE"


class AgentHeartbeat(BaseModel):
    """Heartbeat signal sent periodically by agents."""

    agent_id: str
    timestamp: datetime = Field(default_factory=utc_now)
    monitoring_active: bool = True
