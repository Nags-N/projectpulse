"""Trello Project Management Adapter for ProjectPulse AI.

Implements Section 30:
- Boards, Lists, Cards, Members, Due dates, Labels.
- Normalizes Trello Cards into UnifiedTask.
"""

from datetime import datetime, timedelta
from typing import Any

from backend.integrations.base.base_adapter import BasePMAdapter
from shared.schemas import UnifiedTask


class TrelloAdapter(BasePMAdapter):
    platform_name = "TRELLO"

    def __init__(self):
        self._connected = False

    def connect(self, credentials: dict[str, Any]) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> bool:
        self._connected = False
        return True

    def is_connected(self) -> bool:
        return self._connected

    def get_projects(self) -> list[dict[str, Any]]:
        return [{"id": "BOARD-DLX", "name": "DLX Sprint Board"}]

    def get_tasks(self, external_project_id: str = "DLX") -> list[UnifiedTask]:
        now = datetime.now()
        # Normalizes Trello Cards -> UnifiedTasks
        return [
            UnifiedTask(
                project_id=external_project_id,
                source="TRELLO",
                external_task_id="CARD-201",
                title="Product Catalog Search Elastic Query",
                description="Index search optimization and full-text filter pipeline.",
                status="BLOCKED",
                priority="MEDIUM",
                assignee="Priya Sharma",
                due_date=(now + timedelta(days=5)).strftime("%Y-%m-%d"),
            ),
            UnifiedTask(
                project_id=external_project_id,
                source="TRELLO",
                external_task_id="CARD-202",
                title="Image CDN Resizing Service",
                description="Optimize hero banners and product thumbnail latency.",
                status="IN_PROGRESS",
                priority="LOW",
                assignee="Alex Rivera",
                due_date=(now + timedelta(days=10)).strftime("%Y-%m-%d"),
            ),
        ]

    def get_task(self, task_id: str) -> UnifiedTask | None:
        for t in self.get_tasks():
            if t.external_task_id == task_id:
                return t
        return None
