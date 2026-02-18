"""Tests for src/phases/api_handlers.py."""

import json
from unittest.mock import MagicMock, patch

import pytest
from src.state.models import Phase, PhaseStatus, TaskLedger


@pytest.mark.unit
class TestCreateProjectHandler:
    """Verify create_project_handler behavior."""

    @patch("src.phases.api_handlers.STATE_MACHINE_ARN", "")
    @patch("src.phases.api_handlers.SOW_BUCKET", "")
    @patch("src.phases.api_handlers.write_ledger")
    def test_creates_project(self, mock_write: MagicMock) -> None:
        from src.phases.api_handlers import create_project_handler

        event = {
            "body": json.dumps(
                {
                    "project_name": "Test Project",
                    "customer": "Acme Corp",
                    "sow_text": "Build a data lake",
                }
            ),
        }

        result = create_project_handler(event)

        assert result["statusCode"] == 201
        body = json.loads(result["body"])
        assert body["project_name"] == "Test Project"
        assert body["status"] == "CREATED"
        assert "project_id" in body
        mock_write.assert_called_once()

    def test_rejects_missing_fields(self) -> None:
        from src.phases.api_handlers import create_project_handler

        event = {"body": json.dumps({"customer": "Acme"})}
        result = create_project_handler(event)
        assert result["statusCode"] == 400


@pytest.mark.unit
class TestProjectStatusHandler:
    """Verify project_status_handler behavior."""

    @patch("src.phases.api_handlers.read_ledger")
    def test_returns_status(self, mock_read: MagicMock) -> None:
        from src.phases.api_handlers import project_status_handler

        mock_read.return_value = TaskLedger(
            project_id="proj-1",
            project_name="Test",
            current_phase=Phase.ARCHITECTURE,
            phase_status=PhaseStatus.IN_PROGRESS,
        )

        event = {"pathParameters": {"id": "proj-1"}}
        result = project_status_handler(event)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["current_phase"] == "ARCHITECTURE"
        assert body["phase_status"] == "IN_PROGRESS"

    def test_rejects_missing_id(self) -> None:
        from src.phases.api_handlers import project_status_handler

        event = {"pathParameters": {}}
        result = project_status_handler(event)
        assert result["statusCode"] == 400


@pytest.mark.unit
class TestApproveHandler:
    """Verify approve_handler behavior."""

    @patch("src.phases.api_handlers.delete_token")
    @patch("src.phases.api_handlers.boto3")
    @patch("src.phases.api_handlers.get_token")
    @patch("src.phases.api_handlers.read_ledger")
    def test_approves_phase(
        self,
        mock_read: MagicMock,
        mock_get_token: MagicMock,
        mock_boto3: MagicMock,
        mock_delete: MagicMock,
    ) -> None:
        from src.phases.api_handlers import approve_handler

        mock_read.return_value = TaskLedger(
            project_id="proj-1",
            current_phase=Phase.DISCOVERY,
        )
        mock_get_token.return_value = "token-abc"
        mock_sfn = MagicMock()
        mock_boto3.client.return_value = mock_sfn

        event = {"pathParameters": {"id": "proj-1"}}
        result = approve_handler(event)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["decision"] == "APPROVED"
        mock_sfn.send_task_success.assert_called_once()
        mock_delete.assert_called_once()

    @patch("src.phases.api_handlers.get_token")
    @patch("src.phases.api_handlers.read_ledger")
    def test_404_when_no_token(
        self,
        mock_read: MagicMock,
        mock_get_token: MagicMock,
    ) -> None:
        from src.phases.api_handlers import approve_handler

        mock_read.return_value = TaskLedger(project_id="proj-1")
        mock_get_token.return_value = ""

        event = {"pathParameters": {"id": "proj-1"}}
        result = approve_handler(event)
        assert result["statusCode"] == 404


@pytest.mark.unit
class TestReviseHandler:
    """Verify revise_handler behavior."""

    @patch("src.phases.api_handlers.delete_token")
    @patch("src.phases.api_handlers.boto3")
    @patch("src.phases.api_handlers.get_token")
    @patch("src.phases.api_handlers.read_ledger")
    def test_revise_phase(
        self,
        mock_read: MagicMock,
        mock_get_token: MagicMock,
        mock_boto3: MagicMock,
        _mock_delete: MagicMock,
    ) -> None:
        from src.phases.api_handlers import revise_handler

        mock_read.return_value = TaskLedger(project_id="proj-1")
        mock_get_token.return_value = "token-abc"
        mock_sfn = MagicMock()
        mock_boto3.client.return_value = mock_sfn

        event = {
            "pathParameters": {"id": "proj-1"},
            "body": json.dumps({"feedback": "More detail needed"}),
        }
        result = revise_handler(event)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["decision"] == "REVISION_REQUESTED"
        mock_sfn.send_task_success.assert_called_once()

    def test_rejects_missing_feedback(self) -> None:
        from src.phases.api_handlers import revise_handler

        event = {
            "pathParameters": {"id": "proj-1"},
            "body": json.dumps({}),
        }
        result = revise_handler(event)
        assert result["statusCode"] == 400


@pytest.mark.unit
class TestInterruptRespondHandler:
    """Verify interrupt_respond_handler behavior."""

    @patch("src.phases.api_handlers.store_interrupt_response")
    def test_stores_response(self, mock_store: MagicMock) -> None:
        from src.phases.api_handlers import interrupt_respond_handler

        event = {
            "pathParameters": {"id": "proj-1", "interruptId": "int-001"},
            "body": json.dumps({"response": "Blue"}),
        }
        result = interrupt_respond_handler(event)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "ANSWERED"
        mock_store.assert_called_once_with("cloudcrew-projects", "proj-1", "int-001", "Blue")

    def test_rejects_missing_response(self) -> None:
        from src.phases.api_handlers import interrupt_respond_handler

        event = {
            "pathParameters": {"id": "proj-1", "interruptId": "int-001"},
            "body": json.dumps({}),
        }
        result = interrupt_respond_handler(event)
        assert result["statusCode"] == 400


@pytest.mark.unit
class TestRoute:
    """Verify API route dispatcher."""

    @patch("src.phases.api_handlers.create_project_handler")
    def test_routes_post_projects(self, mock_handler: MagicMock) -> None:
        from src.phases.api_handlers import route

        mock_handler.return_value = {"statusCode": 201, "body": "{}"}
        event = {"httpMethod": "POST", "resource": "/projects"}
        route(event, None)
        mock_handler.assert_called_once_with(event)

    @patch("src.phases.api_handlers.project_status_handler")
    def test_routes_get_status(self, mock_handler: MagicMock) -> None:
        from src.phases.api_handlers import route

        mock_handler.return_value = {"statusCode": 200, "body": "{}"}
        event = {"httpMethod": "GET", "resource": "/projects/{id}/status"}
        route(event, None)
        mock_handler.assert_called_once_with(event)

    def test_returns_404_for_unknown_route(self) -> None:
        from src.phases.api_handlers import route

        event = {"httpMethod": "DELETE", "resource": "/unknown"}
        result = route(event, None)
        assert result["statusCode"] == 404
