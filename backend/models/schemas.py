"""Pydantic API schemas."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_serializer

from shared.events import EventSource, EventType, ProjectEvent, ProjectEventCreate, UserRole


class UserCreate(BaseModel):
    user_id: str | None = None
    name: str
    role: UserRole = UserRole.DEVELOPER


class UserResponse(BaseModel):
    user_id: str
    name: str
    role: UserRole
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectCreate(BaseModel):
    project_id: str | None = None
    name: str
    folder_path: str
    owner_user_id: str


class ProjectResponse(BaseModel):
    project_id: str
    name: str
    folder_path: str
    owner_user_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class EventIngestRequest(ProjectEventCreate):
    event_id: str | None = None


class EventResponse(ProjectEvent):
    created_at: datetime | None = None
    human_description: str = ""
    display_title: str = ""

    model_config = {"from_attributes": True}

    @field_serializer("created_at")
    def _serialize_created_at(self, value: datetime | None) -> str | None:
        from shared.timeutil import to_iso_utc

        return to_iso_utc(value)


class ActivitySummary(BaseModel):
    total_activities: int = 0
    commits: int = 0
    build_failures: int = 0
    build_successes: int = 0
    file_modifications: int = 0
    files_created: int = 0
    branch_changes: int = 0


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


class ManagerDashboardResponse(BaseModel):
    project_id: str
    project_name: str
    activity: ActivitySummary
    recent_events: list[EventResponse] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)
    narrative_summary: str = ""


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


def new_id() -> str:
    return str(uuid4())
