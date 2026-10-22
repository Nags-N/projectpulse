"""Unit and integration tests for Jira Cloud REST API v3 integration in ProjectPulse AI.

Tests cover:
1. ADF text parsing and status/priority normalization.
2. JiraCloudClient error handling, authentication, and pagination (mocking HTTP).
3. JiraService synchronization idempotency (created, updated, unchanged, failed).
4. Webhook payload handling and event generation.
5. Database model persistence and field mapping.
"""

import json
import unittest
from unittest.mock import MagicMock, patch
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.integrations.jira.client import JiraCloudClient, JiraClientError
from backend.integrations.jira.mapper import (
    extract_adf_text,
    jira_issue_to_schema,
    jira_issue_to_task_dict,
    jira_issue_to_unified_task,
    normalize_jira_priority,
    normalize_jira_status,
)
from backend.integrations.jira.schemas import JiraTestConnectionResponse
from backend.integrations.jira.service import JiraService
from backend.models.db_models import JiraConnectionRecord, ProjectEventRecord, SyncRunRecord, TaskRecord


class TestJiraADFAndNormalizers(unittest.TestCase):
    """Test Atlassian Document Format extraction and status/priority normalization."""

    def test_extract_plain_text(self):
        self.assertEqual(extract_adf_text("Simple string"), "Simple string")
        self.assertEqual(extract_adf_text(None), "")
        self.assertEqual(extract_adf_text(123), "123")

    def test_extract_adf_structure(self):
        adf_doc = {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Payment gateway "},
                        {"type": "text", "text": "requires refactoring."},
                    ],
                },
                {
                    "type": "bulletList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Item one"}],
                                }
                            ],
                        }
                    ],
                },
                {
                    "type": "codeBlock",
                    "content": [{"type": "text", "text": "const stripe = require('stripe');"}],
                },
            ],
        }
        text = extract_adf_text(adf_doc)
        self.assertIn("Payment gateway requires refactoring.", text)
        self.assertIn("• Item one", text)
        self.assertIn("const stripe = require('stripe');", text)

    def test_normalize_status(self):
        # Strings
        self.assertEqual(normalize_jira_status("Done"), "COMPLETED")
        self.assertEqual(normalize_jira_status("Closed"), "COMPLETED")
        self.assertEqual(normalize_jira_status("In Progress"), "IN_PROGRESS")
        self.assertEqual(normalize_jira_status("Under Review"), "IN_PROGRESS")
        self.assertEqual(normalize_jira_status("Blocked"), "BLOCKED")
        self.assertEqual(normalize_jira_status("On Hold"), "BLOCKED")
        self.assertEqual(normalize_jira_status("Open"), "TODO")
        self.assertEqual(normalize_jira_status("To Do"), "TODO")

        # Dict with statusCategory
        self.assertEqual(normalize_jira_status({"name": "Custom Done", "statusCategory": {"key": "done"}}), "COMPLETED")
        self.assertEqual(normalize_jira_status({"name": "Backlog", "statusCategory": {"key": "new"}}), "TODO")

    def test_normalize_priority(self):
        self.assertEqual(normalize_jira_priority("Highest"), "URGENT")
        self.assertEqual(normalize_jira_priority("Blocker"), "URGENT")
        self.assertEqual(normalize_jira_priority("High"), "HIGH")
        self.assertEqual(normalize_jira_priority("Medium"), "MEDIUM")
        self.assertEqual(normalize_jira_priority("Low"), "LOW")
        self.assertEqual(normalize_jira_priority("Lowest"), "LOW")
        self.assertEqual(normalize_jira_priority({"name": "Critical"}), "URGENT")


class TestJiraCloudClient(unittest.TestCase):
    """Test JiraCloudClient connection, error translation, and requests."""

    def setUp(self):
        self.client = JiraCloudClient(
            base_url="https://testorg.atlassian.net",
            email="developer@testorg.com",
            api_token="test_token_12345",
        )

    def test_configuration(self):
        self.assertTrue(self.client.is_configured)
        unconfigured = JiraCloudClient(base_url="", email="", api_token="")
        self.assertFalse(unconfigured.is_configured)

    @patch("httpx.Client.get")
    def test_connection_success(self, mock_get):
        # Mock /rest/api/3/myself
        mock_myself_resp = MagicMock()
        mock_myself_resp.status_code = 200
        mock_myself_resp.json.return_value = {
            "displayName": "Alex Rivera",
            "accountId": "acc-12345",
            "emailAddress": "developer@testorg.com",
        }

        # Mock /rest/api/3/project/DLX
        mock_proj_resp = MagicMock()
        mock_proj_resp.status_code = 200
        mock_proj_resp.json.return_value = {
            "key": "DLX",
            "name": "DLX E-Commerce Platform",
        }

        mock_get.side_effect = [mock_myself_resp, mock_proj_resp]

        res = self.client.test_connection(project_key="DLX")
        self.assertTrue(res.success)
        self.assertEqual(res.user_display_name, "Alex Rivera")
        self.assertTrue(res.project_found)
        self.assertEqual(res.project_key, "DLX")

    @patch("httpx.Client.get")
    def test_connection_auth_failure_401(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {"errorMessages": ["Invalid credentials"]}
        mock_resp.text = "Unauthorized"
        
        req = httpx.Request("GET", "https://testorg.atlassian.net/rest/api/3/myself")
        mock_get.side_effect = httpx.HTTPStatusError("401 Unauthorized", request=req, response=mock_resp)

        res = self.client.test_connection(project_key="DLX")
        self.assertFalse(res.success)
        self.assertIn("Authentication failed (401)", res.error_message)

    @patch("httpx.Client.get")
    def test_fetch_all_issues_pagination(self, mock_get):
        # Page 1
        page1 = MagicMock()
        page1.status_code = 200
        page1.json.return_value = {
            "startAt": 0,
            "maxResults": 2,
            "total": 3,
            "issues": [
                {"id": "1", "key": "DLX-1", "fields": {"summary": "Issue 1", "status": {"name": "To Do"}}},
                {"id": "2", "key": "DLX-2", "fields": {"summary": "Issue 2", "status": {"name": "In Progress"}}},
            ],
        }

        # Page 2
        page2 = MagicMock()
        page2.status_code = 200
        page2.json.return_value = {
            "startAt": 2,
            "maxResults": 2,
            "total": 3,
            "issues": [
                {"id": "3", "key": "DLX-3", "fields": {"summary": "Issue 3", "status": {"name": "Done"}}},
            ],
        }

        mock_get.side_effect = [page1, page2]

        all_issues = self.client.fetch_all_issues(project_key="DLX", max_total=50)
        self.assertEqual(len(all_issues), 3)
        self.assertEqual(all_issues[0]["key"], "DLX-1")
        self.assertEqual(all_issues[2]["key"], "DLX-3")


class TestJiraServiceAndSync(unittest.TestCase):
    """Test full JiraService synchronization idempotency and persistence."""

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        self.mock_client = MagicMock(spec=JiraCloudClient)
        self.mock_client.is_configured = True
        self.mock_client.base_url = "https://testorg.atlassian.net"
        self.mock_client.email = "developer@testorg.com"

        self.service = JiraService(db=self.db, client=self.mock_client)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_sync_project_idempotency(self):
        raw_issues = [
            {
                "id": "1001",
                "key": "DLX-101",
                "fields": {
                    "summary": "Payment Gateway Integration",
                    "description": "Implement Stripe payment processing",
                    "status": {"name": "In Progress"},
                    "priority": {"name": "High"},
                    "assignee": {"displayName": "Alice Chen"},
                    "reporter": {"displayName": "Sarah Chen"},
                    "duedate": "2026-09-30",
                    "issuetype": {"name": "Story"},
                    "labels": ["backend", "payments"],
                    "components": [{"name": "Checkout API"}],
                    "customfield_10016": 5.0,
                    "created": "2026-09-20T10:00:00.000+0000",
                    "updated": "2026-09-25T15:30:00.000+0000",
                },
            },
            {
                "id": "1002",
                "key": "DLX-102",
                "fields": {
                    "summary": "User Authentication OAuth2",
                    "description": "Configure JWT verification",
                    "status": {"name": "Done"},
                    "priority": {"name": "Highest"},
                    "assignee": {"displayName": "Marcus Vance"},
                    "reporter": {"displayName": "Sarah Chen"},
                    "duedate": "2026-09-24",
                    "issuetype": {"name": "Story"},
                    "labels": ["security"],
                    "components": [{"name": "Auth Core"}],
                    "customfield_10016": 3.0,
                    "created": "2026-09-18T09:00:00.000+0000",
                    "updated": "2026-09-24T18:00:00.000+0000",
                },
            },
        ]
        self.mock_client.fetch_all_issues.return_value = raw_issues

        # FIRST SYNC: Both tasks are brand new
        res1 = self.service.sync_project("DLX")
        self.assertEqual(res1.status, "SUCCESS")
        self.assertEqual(res1.records_fetched, 2)
        self.assertEqual(res1.records_created, 2)
        self.assertEqual(res1.records_updated, 0)
        self.assertEqual(res1.records_unchanged, 0)

        # Verify DB tasks
        t101 = self.db.query(TaskRecord).filter(TaskRecord.external_task_id == "DLX-101").first()
        self.assertIsNotNone(t101)
        self.assertEqual(t101.title, "Payment Gateway Integration")
        self.assertEqual(t101.status, "IN_PROGRESS")
        self.assertEqual(t101.priority, "HIGH")
        self.assertEqual(t101.story_points, 5.0)
        self.assertEqual(t101.jira_url, "https://testorg.atlassian.net/browse/DLX-101")
        self.assertIn("Checkout API", t101.components)
        self.assertIsNotNone(t101.last_synced_at)

        # Verify timeline events were recorded
        events = self.db.query(ProjectEventRecord).filter(ProjectEventRecord.source == "JIRA").all()
        self.assertEqual(len(events), 2)

        # SECOND SYNC: No changes made to either issue
        res2 = self.service.sync_project("DLX")
        self.assertEqual(res2.status, "SUCCESS")
        self.assertEqual(res2.records_fetched, 2)
        self.assertEqual(res2.records_created, 0)
        self.assertEqual(res2.records_updated, 0)
        self.assertEqual(res2.records_unchanged, 2)

        # THIRD SYNC: Modify DLX-101 status from In Progress to Done
        raw_issues[0]["fields"]["status"] = {"name": "Done"}
        res3 = self.service.sync_project("DLX")
        self.assertEqual(res3.status, "SUCCESS")
        self.assertEqual(res3.records_created, 0)
        self.assertEqual(res3.records_updated, 1)
        self.assertEqual(res3.records_unchanged, 1)

        t101_updated = self.db.query(TaskRecord).filter(TaskRecord.external_task_id == "DLX-101").first()
        self.assertEqual(t101_updated.status, "COMPLETED")

    def test_webhook_handler(self):
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "id": "1003",
                "key": "DLX-103",
                "fields": {
                    "project": {"key": "DLX"},
                    "summary": "Real-time Webhook Issue",
                    "description": "Created via webhook notification",
                    "status": {"name": "In Progress"},
                    "priority": {"name": "Medium"},
                    "assignee": {"displayName": "Priya Sharma"},
                    "reporter": {"displayName": "Sarah Chen"},
                    "issuetype": {"name": "Bug"},
                },
            },
            "user": {"displayName": "Priya Sharma"},
        }

        res = self.service.handle_webhook(payload, self.db)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["action"], "created")
        self.assertEqual(res["task_id"], "DLX-103")

class TestJiraApiRouter(unittest.TestCase):
    """Test FastAPI Jira REST endpoints."""

    def setUp(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        self.client = TestClient(app)

    def test_api_jira_info(self):
        res = self.client.get("/api/integrations/jira/info")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["platform"], "JIRA")
        self.assertIn("connected", data)
        self.assertIn("masked_token", data)

    @patch("backend.integrations.jira.service.JiraService.test_connection")
    def test_api_jira_test_endpoint(self, mock_test):
        mock_test.return_value = JiraTestConnectionResponse(
            success=True,
            user_display_name="Sarah Chen",
            account_id="acc-777",
            email="sarah@testorg.com",
            project_found=True,
            project_key="DLX",
            project_name="DLX E-Commerce Platform",
            base_url="https://testorg.atlassian.net",
        )
        res = self.client.get("/api/integrations/jira/test?project_key=DLX")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user_display_name"], "Sarah Chen")
        self.assertEqual(data["project_key"], "DLX")

    @patch("backend.integrations.jira.service.JiraService.get_issues")
    def test_api_jira_issues_endpoint(self, mock_issues):
        from backend.integrations.jira.schemas import JiraIssueItem
        mock_issues.return_value = [
            JiraIssueItem(
                key="DLX-201",
                summary="Payment API Integration",
                status="IN_PROGRESS",
                priority="HIGH",
                jira_url="https://testorg.atlassian.net/browse/DLX-201",
            )
        ]
        res = self.client.get("/api/integrations/jira/issues?project_id=DLX")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["key"], "DLX-201")
        self.assertEqual(data[0]["jira_url"], "https://testorg.atlassian.net/browse/DLX-201")

    @patch("backend.integrations.jira.service.JiraService.sync_project")
    def test_api_jira_sync_endpoint(self, mock_sync):
        from backend.integrations.jira.schemas import JiraSyncStatsResponse
        mock_sync.return_value = JiraSyncStatsResponse(
            status="SUCCESS",
            records_fetched=10,
            records_created=2,
            records_updated=1,
            records_unchanged=7,
            records_failed=0,
            project_key="DLX",
            duration_sec=0.85,
            synced_at="2026-09-26T12:00:00",
        )
        res = self.client.post("/api/integrations/jira/sync", json={"project_id": "DLX", "jira_project_key": "DLX"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["records_fetched"], 10)
        self.assertEqual(data["records_created"], 2)


if __name__ == "__main__":
    unittest.main()
