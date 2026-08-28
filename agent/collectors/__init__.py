"""Source collectors — VS Code file watcher and future Git/Build collectors."""

import logging

from agent.backend_client import BackendClient
from agent.collectors.base import BaseCollector
from agent.collectors.file_watcher import ProjectFileWatcherCollector
from agent.collectors.git_watcher import GitActivityCollector
from agent.config import AgentConfig
from agent.normalizer import EventNormalizer
from agent.privacy_filter import PrivacyFilter

logger = logging.getLogger(__name__)


class CollectorManager:
    """Manages VS Code, Git, Terminal, and Build collectors."""

    def __init__(self, config: AgentConfig, backend: BackendClient):
        self.config = config
        self.backend = backend
        self.normalizer = EventNormalizer(config)
        self.privacy_filter = PrivacyFilter(config)
        self._collectors: list[BaseCollector] = []
        self._events_sent = 0

    @property
    def events_sent(self) -> int:
        return self._events_sent

    def _on_event_sent(self, _event) -> None:
        self._events_sent += 1

    def _build_collectors(self) -> list[BaseCollector]:
        common = dict(
            config=self.config,
            normalizer=self.normalizer,
            privacy_filter=self.privacy_filter,
            backend=self.backend,
            on_event_sent=self._on_event_sent,
        )
        collectors: list[BaseCollector] = []

        if "VS_CODE" in self.config.allowed_sources:
            collectors.append(ProjectFileWatcherCollector(**common))

        if "GIT" in self.config.allowed_sources:
            collectors.append(GitActivityCollector(**common))

        # Terminal, Build collectors added in Milestone 4
        return collectors

    def start(self) -> None:
        if self._collectors:
            return

        if not self.config.monitoring_active:
            logger.info("Monitoring paused — collectors not started")
            return

        self._collectors = self._build_collectors()
        for collector in self._collectors:
            try:
                collector.start()
                logger.info("Started collector: %s", collector.source_name)
            except Exception as exc:
                logger.error("Failed to start %s: %s", collector.source_name, exc)

    def stop(self) -> None:
        for collector in self._collectors:
            try:
                collector.stop()
            except Exception as exc:
                logger.error("Failed to stop %s: %s", collector.source_name, exc)
        self._collectors.clear()

    def restart(self) -> None:
        """Restart collectors (e.g. after config change or resume monitoring)."""
        self.stop()
        self.start()
