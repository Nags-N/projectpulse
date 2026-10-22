"""Real Jira Cloud Project Management Adapter for ProjectPulse AI.

Implements Sections 12, 27 & Feature 4:
- Secure Jira Cloud REST API v3 Integration with Basic Auth (email + API token).
- Real project and issue synchronization with JQL query support and pagination.
- Full normalization from Jira ADF & REST format into unified ProjectPulse Task model.
- Strictly uses real Jira Cloud data without fabricated or mock data in production.
"""

from datetime import datetime
import logging
from typing import Any

from backend.config import settings
from backend.integrations.base.base_adapter import BasePMAdapter
from backend.integrations.jira.client import JiraCloudClient
from backend.integrations.jira.mapper import (
    extract_adf_text,
    jira_issue_to_unified_task,
    normalize_jira_priority,
    normalize_jira_status,
)
from shared.schemas import UnifiedTask

logger = logging.getLogger(__name__)


class JiraAdapter(BasePMAdapter):
    platform_name = "JIRA"

    def __init__(self):
        self._client = JiraCloudClient()
        self._connected = False
        self._last_error = None
        self._user_display_name = ""

        # Auto-connect if environment variables are configured
        if self._client.is_configured:
            try:
                res = self._client.test_connection()
                if res.success:
                    self._connected = True
                    self._user_display_name = res.user_display_name
                else:
                    self._connected = False
                    self._last_error = res.error_message
            except Exception as exc:
                self._connected = False
                self._last_error = str(exc)

    def connect(self, credentials: dict[str, Any]) -> bool:
        """Connect to live Jira Cloud REST API v3 using provided credentials."""
        base_url = credentials.get("base_url") or settings.jira_base_url
        email = credentials.get("email") or settings.jira_email
        api_token = credentials.get("api_token") or settings.jira_api_token

        self._client = JiraCloudClient(base_url=base_url, email=email, api_token=api_token)
        test_res = self._client.test_connection(project_key=settings.jira_project_key)

        if test_res.success:
            self._connected = True
            self._user_display_name = test_res.user_display_name
            self._last_error = None
            logger.info("Successfully connected to live Jira Cloud as %s", self._user_display_name)
            return True
        else:
            self._connected = False
            self._last_error = test_res.error_message
            logger.warning("Failed to connect to Jira Cloud: %s", test_res.error_message)
            return False

    def disconnect(self) -> bool:
        """Disconnect and clear active credentials."""
        self._connected = False
        self._user_display_name = ""
        self._client = JiraCloudClient(base_url="", email="", api_token="")
        return True

    def is_connected(self) -> bool:
        return self._connected

    def get_connection_info(self) -> dict[str, Any]:
        token = self._client.api_token
        masked_token = (token[:4] + "********") if len(token) > 4 else ("********" if token else "")
        return {
            "platform": "JIRA",
            "connected": self._connected,
            "base_url": self._client.base_url or settings.jira_base_url or "https://your-domain.atlassian.net",
            "email": self._client.email or settings.jira_email or "",
            "masked_token": masked_token,
            "project_key": settings.jira_project_key or "DLX",
            "user_display_name": self._user_display_name,
            "error_message": self._last_error,
        }

    def get_projects(self) -> list[dict[str, Any]]:
        """Fetch accessible projects from Jira Cloud."""
        if not self._client.is_configured:
            return []

        try:
            import httpx
            with httpx.Client(timeout=10.0) as client:
                res = client.get(
                    f"{self._client.base_url}/rest/api/3/project/search",
                    auth=(self._client.email, self._client.api_token),
                    headers={"Accept": "application/json"},
                )
                if res.status_code == 200:
                    data = res.json()
                    projects = []
                    for p in data.get("values", []):
                        projects.append({
                            "id": str(p.get("id", "")),
                            "key": p.get("key", ""),
                            "name": p.get("name", ""),
                            "lead": p.get("lead", {}).get("displayName", "") if isinstance(p.get("lead"), dict) else "",
                        })
                    return projects
        except Exception as exc:
            logger.warning("Failed to fetch live Jira projects: %s", exc)

        return []

    def get_tasks(self, external_project_id: str = "DLX") -> list[UnifiedTask]:
        """Fetch real Jira issues for the project using JQL search with pagination."""
        if not self._client.is_configured:
            return []

        try:
            raw_issues = self._client.fetch_all_issues(project_key=external_project_id, max_total=500)
            tasks = []
            for issue in raw_issues:
                unified = jira_issue_to_unified_task(issue, self._client.base_url, external_project_id)
                tasks.append(unified)
            return tasks
        except Exception as exc:
            logger.error("Failed to fetch live Jira tasks for %s: %s", external_project_id, exc)
            return []

    def get_task(self, task_id: str) -> UnifiedTask | None:
        """Fetch a single live Jira issue by ID or Key."""
        if not self._client.is_configured:
            return None

        try:
            raw_issue = self._client.get_issue(task_id)
            proj_key = raw_issue.get("fields", {}).get("project", {}).get("key", "DLX")
            return jira_issue_to_unified_task(raw_issue, self._client.base_url, proj_key)
        except Exception as exc:
            logger.warning("Failed to fetch Jira task %s: %s", task_id, exc)
            return None

    def get_comments(self, task_id: str) -> list[dict[str, Any]]:
        """Fetch comments for a live Jira issue."""
        if not self._client.is_configured:
            return []
        try:
            return self._client.get_comments(task_id)
        except Exception as exc:
            logger.warning("Failed to fetch comments for Jira task %s: %s", task_id, exc)
            return []
