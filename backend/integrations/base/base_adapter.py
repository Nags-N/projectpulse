"""Common adapter interface for external Project Management platforms.

Implements Section 26 of the ProjectPulse AI Master Architecture:
- connect()
- get_projects()
- get_tasks(project_id)
- get_task(task_id)
- get_users()
- get_comments(task_id)
- get_activity(project_id)
- disconnect()
"""

from abc import ABC, abstractmethod
from typing import Any

from shared.schemas import UnifiedTask


class BasePMAdapter(ABC):
    """Abstract base class that all PM adapters (Jira, monday, Asana, Trello, ClickUp, Linear) must implement."""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Name of the platform (e.g. JIRA, MONDAY, ASANA, TRELLO, CLICKUP, LINEAR)."""
        pass

    @abstractmethod
    def connect(self, credentials: dict[str, Any]) -> bool:
        """Authenticate and establish connection with the external platform."""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Sever connection and invalidate active session tokens."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if currently authenticated and ready."""
        pass

    @abstractmethod
    def get_projects(self) -> list[dict[str, Any]]:
        """Retrieve accessible projects or workspaces from the platform."""
        pass

    @abstractmethod
    def get_tasks(self, external_project_id: str) -> list[UnifiedTask]:
        """Fetch and normalize all tasks/issues/cards into UnifiedTask models."""
        pass

    @abstractmethod
    def get_task(self, task_id: str) -> UnifiedTask | None:
        """Fetch a single normalized task by ID."""
        pass

    def get_users(self) -> list[dict[str, Any]]:
        """Retrieve team members from the platform if supported."""
        return []

    def get_comments(self, task_id: str) -> list[dict[str, Any]]:
        """Retrieve task comments if supported."""
        return []

    def get_activity(self, project_id: str) -> list[dict[str, Any]]:
        """Retrieve external project audit activity if supported."""
        return []
