"""Common ProjectEvent schema — all sources normalize to this format."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_serializer

from shared.event_types import EventSource, EventType, UserRole
from shared.timeutil import to_iso_utc, utc_now

__all__ = [
    "UserRole",
    "EventSource",
    "EventType",
    "ProjectEventCreate",
    "ProjectEvent",
]


class ProjectEventCreate(BaseModel):
    """Payload sent by agents and integration adapters to the backend."""

    event_id: str | None = None
    agent_id: str = "AGENT-DEFAULT"
    project_id: str
    user_id: str
    role: UserRole = UserRole.DEVELOPER
    source: EventSource
    event_type: EventType
    title: str
    description: str = ""
    status: str = "INFO"
    timestamp: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_serializer("timestamp")
    def _serialize_timestamp(self, value: datetime) -> str:
        return to_iso_utc(value) or ""


class ProjectEvent(ProjectEventCreate):
    """Full event record including server-assigned event ID."""

    event_id: str = Field(default_factory=lambda: f"EVT-{uuid4().hex[:8].upper()}")

    model_config = {"from_attributes": True}
