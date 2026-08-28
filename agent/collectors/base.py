"""Base collector interface for all activity sources."""

from abc import ABC, abstractmethod

from agent.backend_client import BackendClient
from agent.config import AgentConfig
from agent.normalizer import EventNormalizer
from agent.privacy_filter import PrivacyFilter
from shared.events import ProjectEventCreate


class BaseCollector(ABC):
    """Adapter base — each source (VS Code, Git, Build) implements this."""

    source_name: str = "UNKNOWN"

    def __init__(
        self,
        config: AgentConfig,
        normalizer: EventNormalizer,
        privacy_filter: PrivacyFilter,
        backend: BackendClient,
        on_event_sent=None,
    ):
        self.config = config
        self.normalizer = normalizer
        self.privacy_filter = privacy_filter
        self.backend = backend
        self.on_event_sent = on_event_sent
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def emit(self, event: ProjectEventCreate | None) -> bool:
        """Normalize and send event to backend."""
        if event is None:
            return False
        if not self.privacy_filter.allow_event():
            return False
        sent = self.backend.send_event(event)
        if sent and self.on_event_sent:
            self.on_event_sent(event)
        return sent

    @abstractmethod
    def start(self) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass
