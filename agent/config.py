"""Agent configuration — allowlist-based project folder monitoring."""

import json
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "config" / "agent_config.json"


@dataclass
class AgentConfig:
    project_name: str = "Unconfigured Project"
    project_folder: str = ""
    project_id: str = ""
    user_id: str = ""
    user_name: str = "Developer"
    backend_url: str = "http://127.0.0.1:8000"
    frontend_url: str = "http://127.0.0.1:5173"
    monitoring_active: bool = True
    allowed_sources: list[str] = field(
        default_factory=lambda: ["VS_CODE", "GIT", "TERMINAL", "BUILD"]
    )

    @property
    def project_path(self) -> Path | None:
        if not self.project_folder:
            return None
        return Path(self.project_folder).resolve()

    def is_path_allowed(self, path: Path) -> bool:
        """Privacy filter: only paths inside the configured project folder."""
        if not self.monitoring_active:
            return False
        project = self.project_path
        if project is None or not project.exists():
            return False
        try:
            path.resolve().relative_to(project)
            return True
        except ValueError:
            return False

    def save(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(
                {
                    "project_name": self.project_name,
                    "project_folder": self.project_folder,
                    "project_id": self.project_id,
                    "user_id": self.user_id,
                    "user_name": self.user_name,
                    "backend_url": self.backend_url,
                    "frontend_url": self.frontend_url,
                    "monitoring_active": self.monitoring_active,
                    "allowed_sources": self.allowed_sources,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls) -> "AgentConfig":
        if not CONFIG_PATH.exists():
            cfg = cls()
            cfg.save()
            return cfg
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return cls(
            project_name=data.get("project_name", "Unconfigured Project"),
            project_folder=data.get("project_folder", ""),
            project_id=data.get("project_id", ""),
            user_id=data.get("user_id", ""),
            user_name=data.get("user_name", "Developer"),
            backend_url=data.get("backend_url", "http://127.0.0.1:8000"),
            frontend_url=data.get("frontend_url", "http://127.0.0.1:5173"),
            monitoring_active=data.get("monitoring_active", True),
            allowed_sources=data.get(
                "allowed_sources", ["VS_CODE", "GIT", "TERMINAL", "BUILD"]
            ),
        )
