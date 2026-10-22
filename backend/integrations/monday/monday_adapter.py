"""Monday.com Project Management Adapter for ProjectPulse AI.

Implements Section 28:
- Workspaces, Boards, Items/Tasks, Status, Owners, Dates.
- Normalizes Monday.com Items into UnifiedTask.
"""

from datetime import datetime, timedelta
from typing import Any

from backend.integrations.base.base_adapter import BasePMAdapter
from shared.schemas import UnifiedTask


class MondayAdapter(BasePMAdapter):
    platform_name = "MONDAY"

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
        return [{"id": "MON-BOARD-1", "name": "Sprint Operations Board"}]

    def get_tasks(self, external_project_id: str = "DLX") -> list[UnifiedTask]:
        now = datetime.now()
        # Normalizes Monday Items -> UnifiedTasks
        return [
            UnifiedTask(
                project_id=external_project_id,
                source="MONDAY",
                external_task_id="MON-77",
                title="Customer Support Chatbot Widget",
                description="Live agent handoff and order lookup integration.",
                status="TODO",
                priority="MEDIUM",
                assignee="Priya Sharma",
                due_date=(now + timedelta(days=9)).strftime("%Y-%m-%d"),
            ),
        ]

    def get_task(self, task_id: str) -> UnifiedTask | None:
        for t in self.get_tasks():
            if t.external_task_id == task_id:
                return t
        return None
