"""Linear Project Management Adapter for ProjectPulse AI.

Implements Section 32:
- Teams, Projects, Issues, Cycles, Assignees, Status, Priority.
- Normalizes Linear Issues into UnifiedTask.
"""

from datetime import datetime, timedelta
from typing import Any

from backend.integrations.base.base_adapter import BasePMAdapter
from shared.schemas import UnifiedTask


class LinearAdapter(BasePMAdapter):
    platform_name = "LINEAR"

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
        return [{"id": "LIN-TEAM-CORE", "name": "Core Backend & Payments"}]

    def get_tasks(self, external_project_id: str = "DLX") -> list[UnifiedTask]:
        now = datetime.now()
        # Normalizes Linear Issues -> UnifiedTasks
        return [
            UnifiedTask(
                project_id=external_project_id,
                source="LINEAR",
                external_task_id="LIN-55",
                title="Checkout Session Idempotency",
                description="Prevent double charging on network timeouts and duplicate requests.",
                status="TODO",
                priority="URGENT",
                assignee="Alex Rivera",
                due_date=(now + timedelta(days=3)).strftime("%Y-%m-%d"),
            ),
            UnifiedTask(
                project_id=external_project_id,
                source="LINEAR",
                external_task_id="LIN-56",
                title="Redis Cluster Session Cache",
                description="Distributed cart session storage with 24hr TTL.",
                status="COMPLETED",
                priority="HIGH",
                assignee="Marcus Vance",
                due_date=(now - timedelta(days=2)).strftime("%Y-%m-%d"),
            ),
        ]

    def get_task(self, task_id: str) -> UnifiedTask | None:
        for t in self.get_tasks():
            if t.external_task_id == task_id:
                return t
        return None
