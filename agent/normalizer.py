"""Convert source-specific activity into common ProjectEvent format."""

from datetime import datetime

from agent.config import AgentConfig
from shared.events import EventSource, EventType, ProjectEventCreate, UserRole
from shared.timeutil import utc_now


class EventNormalizer:
    """All collectors produce normalized ProjectEventCreate objects."""

    def __init__(self, config: AgentConfig):
        self.config = config

    def normalize(
        self,
        source: EventSource,
        event_type: EventType,
        title: str,
        description: str = "",
        status: str = "INFO",
        metadata: dict | None = None,
        timestamp: datetime | None = None,
    ) -> ProjectEventCreate | None:
        if not self.config.monitoring_active:
            return None
        if source.value not in self.config.allowed_sources:
            return None
        if not self.config.project_id or not self.config.user_id:
            return None

        return ProjectEventCreate(
            project_id=self.config.project_id,
            user_id=self.config.user_id,
            role=UserRole.DEVELOPER,
            source=source,
            event_type=event_type,
            title=title,
            description=description,
            status=status,
            timestamp=timestamp or utc_now(),
            metadata=metadata or {},
        )
# Git tracking test