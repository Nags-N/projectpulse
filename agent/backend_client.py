"""HTTP client for sending normalized events to the backend."""

import logging

import httpx

from agent.config import AgentConfig
from agent.event_queue import EventQueue
from shared.events import ProjectEventCreate

logger = logging.getLogger(__name__)


class BackendClient:
    def __init__(self, config: AgentConfig, event_queue: EventQueue | None = None):
        self.config = config
        self.base_url = config.backend_url.rstrip("/")
        self.event_queue = event_queue or EventQueue()
        self._registered = False

    @property
    def is_ready(self) -> bool:
        return bool(self.config.project_id and self.config.user_id)

    def health_check(self) -> bool:
        try:
            response = httpx.get(f"{self.base_url}/api/health", timeout=3.0)
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def send_event(self, event: ProjectEventCreate) -> bool:
        if not self.config.monitoring_active:
            return False

        if not self.is_ready:
            self.event_queue.enqueue(event)
            return False

        try:
            payload = event.model_dump(mode="json")
            response = httpx.post(
                f"{self.base_url}/api/events",
                json=payload,
                timeout=5.0,
            )
            if response.status_code == 201:
                return True
            logger.warning("Backend rejected event: %s", response.text)
            return False
        except httpx.HTTPError as exc:
            logger.warning("Failed to send event: %s", exc)
            self.event_queue.enqueue(event)
            return False

    def get_developer_summary(self) -> dict | None:
        if not self.is_ready:
            return None
        try:
            response = httpx.get(
                f"{self.base_url}/api/projects/{self.config.project_id}/summary",
                params={"user_id": self.config.user_id},
                timeout=5.0,
            )
            if response.status_code == 200:
                return response.json()
            logger.warning("Summary request failed: %s", response.text)
            return None
        except httpx.HTTPError as exc:
            logger.warning("Failed to load developer summary: %s", exc)
            return None

    def set_monitoring_status(self, active: bool) -> bool:
        try:
            response = httpx.post(
                f"{self.base_url}/api/monitoring-status",
                json={"active": active, "project_id": self.config.project_id or None},
                timeout=5.0,
            )
            return response.status_code == 200
        except httpx.HTTPError as exc:
            logger.warning("Failed to update monitoring status: %s", exc)
            return False

    def ensure_registered(self) -> bool:
        """Register user and project with backend if IDs are missing."""
        if not self.health_check():
            return False

        try:
            if not self.config.user_id:
                response = httpx.post(
                    f"{self.base_url}/api/users",
                    json={"name": self.config.user_name, "role": "DEVELOPER"},
                    timeout=5.0,
                )
                response.raise_for_status()
                self.config.user_id = response.json()["user_id"]

            if not self.config.project_id and self.config.project_folder:
                response = httpx.post(
                    f"{self.base_url}/api/projects",
                    json={
                        "name": self.config.project_name,
                        "folder_path": self.config.project_folder,
                        "owner_user_id": self.config.user_id,
                    },
                    timeout=5.0,
                )
                response.raise_for_status()
                self.config.project_id = response.json()["project_id"]

            self.config.save()
            self._registered = True
            self.flush_queue()
            return True
        except httpx.HTTPError as exc:
            logger.warning("Backend registration failed: %s", exc)
            return False

    def flush_queue(self) -> int:
        if not self.is_ready:
            return 0
        return self.event_queue.flush(self._send_direct)

    def _send_direct(self, event: ProjectEventCreate) -> bool:
        try:
            payload = event.model_dump(mode="json")
            response = httpx.post(
                f"{self.base_url}/api/events",
                json=payload,
                timeout=5.0,
            )
            return response.status_code == 201
        except httpx.HTTPError:
            return False
