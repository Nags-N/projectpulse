"""Integration Registry & Connection Manager for ProjectPulse AI."""

from typing import Any
from backend.integrations.asana.asana_adapter import AsanaAdapter
from backend.integrations.base.base_adapter import BasePMAdapter
from backend.integrations.clickup.clickup_adapter import ClickUpAdapter
from backend.integrations.jira.jira_adapter import JiraAdapter
from backend.integrations.linear.linear_adapter import LinearAdapter
from backend.integrations.monday.monday_adapter import MondayAdapter
from backend.integrations.trello.trello_adapter import TrelloAdapter


class IntegrationManager:
    """Manages adapter connections across Jira, monday, Asana, Trello, ClickUp, and Linear."""

    def __init__(self):
        self._adapters: dict[str, BasePMAdapter] = {
            "JIRA": JiraAdapter(),
            "MONDAY": MondayAdapter(),
            "ASANA": AsanaAdapter(),
            "TRELLO": TrelloAdapter(),
            "CLICKUP": ClickUpAdapter(),
            "LINEAR": LinearAdapter(),
        }
        # Pre-connect Jira, Trello, Linear by default for seamless demonstration
        self._adapters["JIRA"].connect({})
        self._adapters["TRELLO"].connect({})
        self._adapters["LINEAR"].connect({})

    def get_adapter(self, platform: str) -> BasePMAdapter | None:
        return self._adapters.get(platform.upper())

    def list_integrations(self) -> list[dict[str, Any]]:
        results = []
        for name, adapter in self._adapters.items():
            results.append({
                "platform": name,
                "connected": adapter.is_connected(),
                "status": "CONNECTED" if adapter.is_connected() else "NOT_CONNECTED",
                "supported_operations": ["get_projects", "get_tasks", "get_task", "connect", "disconnect"],
            })
        return results

    def connect_platform(self, platform: str, credentials: dict[str, Any]) -> bool:
        adapter = self.get_adapter(platform)
        if not adapter:
            return False
        return adapter.connect(credentials)

    def disconnect_platform(self, platform: str) -> bool:
        adapter = self.get_adapter(platform)
        if not adapter:
            return False
        return adapter.disconnect()


integration_manager = IntegrationManager()
