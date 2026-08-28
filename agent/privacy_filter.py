"""Privacy filter — allowlist-only path validation."""

from pathlib import Path

from agent.config import AgentConfig


class PrivacyFilter:
    """
    Ensures the agent only processes activity within the
    explicitly configured project folder. Nothing else is collected.
    """

    def __init__(self, config: AgentConfig):
        self.config = config

    @property
    def is_active(self) -> bool:
        return self.config.monitoring_active

    def allow_path(self, path: Path | str) -> bool:
        return self.config.is_path_allowed(Path(path))

    def allow_event(self) -> bool:
        return self.config.monitoring_active and self.config.project_path is not None
