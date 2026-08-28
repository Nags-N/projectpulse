"""Common ProjectEvent schema — all sources normalize to this format."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_serializer

from shared.timeutil import to_iso_utc, utc_now


class UserRole(str, Enum):
    DEVELOPER = "DEVELOPER"
    PROJECT_MANAGER = "PROJECT_MANAGER"


class EventSource(str, Enum):
    VS_CODE = "VS_CODE"
    GIT = "GIT"
    TERMINAL = "TERMINAL"
    BUILD = "BUILD"


class EventType(str, Enum):
    # VS Code
    PROJECT_OPENED = "PROJECT_OPENED"
    FILE_OPENED = "FILE_OPENED"
    FILE_CREATED = "FILE_CREATED"
    FILE_MODIFIED = "FILE_MODIFIED"
    PROJECT_SESSION_STARTED = "PROJECT_SESSION_STARTED"
    PROJECT_SESSION_ENDED = "PROJECT_SESSION_ENDED"

    # Git
    GIT_COMMIT = "GIT_COMMIT"
    GIT_BRANCH_CREATED = "GIT_BRANCH_CREATED"
    GIT_BRANCH_CHANGED = "GIT_BRANCH_CHANGED"
    GIT_PULL = "GIT_PULL"
    GIT_PUSH = "GIT_PUSH"

    # Build
    BUILD_STARTED = "BUILD_STARTED"
    BUILD_SUCCEEDED = "BUILD_SUCCEEDED"
    BUILD_FAILED = "BUILD_FAILED"


class ProjectEventCreate(BaseModel):
    """Payload sent by the agent to the backend."""

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
    """Full event record including server-assigned ID."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))

    model_config = {"from_attributes": True}
