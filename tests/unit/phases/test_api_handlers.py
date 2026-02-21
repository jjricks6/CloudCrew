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
class TestPmChatPostHandler:
    """Verify pm_chat_post_handler behavior."""

    @patch("src.phases.api_handlers.PM_CHAT_LAMBDA_NAME", "cloudcrew-pm-chat")
    @patch("src.phases.api_handlers.boto3")
    @patch("src.phases.api_handlers.broadcast_to_project")
    @patch("src.phases.api_handlers.store_chat_message")
    @patch("src.phases.api_handlers.read_ledger")
    def test_sends_chat_message(
        self,
        mock_read: MagicMock,
        mock_store: MagicMock,
        mock_broadcast: MagicMock,
        mock_boto3: MagicMock,
    ) -> None:
        from src.phases.api_handlers import pm_chat_post_handler

        mock_read.return_value = TaskLedger(
            project_id="proj-1",
            current_phase=Phase.DISCOVERY,
        )

        event = {
            "pathParameters": {"id": "proj-1"},
            "body": json.dumps({"message": "Hello PM"}),
        }
        result = pm_chat_post_handler(event)

        assert result["statusCode"] == 202
        body = json.loads(result["body"])
        assert "message_id" in body

        # Customer message stored
        mock_store.assert_called_once()
        call_kwargs = mock_store.call_args
        assert call_kwargs[1]["role"] == "customer" or call_kwargs[0][3] == "customer"

        # Broadcast sent with correct phase
        mock_broadcast.assert_called_once()
        broadcast_payload = mock_broadcast.call_args[0][1]
        assert broadcast_payload["event"] == "chat_message"
        assert broadcast_payload["phase"] == "DISCOVERY"
        assert broadcast_payload["role"] == "customer"

        # PM Chat Lambda invoked async
        mock_lambda = mock_boto3.client.return_value
        mock_lambda.invoke.assert_called_once()
        invoke_kwargs = mock_lambda.invoke.call_args[1]
        assert invoke_kwargs["InvocationType"] == "Event"
        payload = json.loads(invoke_kwargs["Payload"])
        assert payload["project_id"] == "proj-1"
        assert payload["customer_message"] == "Hello PM"

    @patch("src.phases.api_handlers.PM_CHAT_LAMBDA_NAME", "")
    @patch("src.phases.api_handlers.broadcast_to_project")
    @patch("src.phases.api_handlers.store_chat_message")
    @patch("src.phases.api_handlers.read_ledger")
    def test_skips_lambda_when_not_configured(
        self,
        mock_read: MagicMock,
        _mock_store: MagicMock,
        _mock_broadcast: MagicMock,
    ) -> None:
        from src.phases.api_handlers import pm_chat_post_handler

        mock_read.return_value = TaskLedger(
            project_id="proj-1",
            current_phase=Phase.DISCOVERY,
        )

        event = {
            "pathParameters": {"id": "proj-1"},
            "body": json.dumps({"message": "Hello"}),
        }
        result = pm_chat_post_handler(event)

        # Still returns 202 — message is stored even without PM response
        assert result["statusCode"] == 202

    def test_rejects_missing_message(self) -> None:
        from src.phases.api_handlers import pm_chat_post_handler

        event = {
            "pathParameters": {"id": "proj-1"},
            "body": json.dumps({}),
        }
        result = pm_chat_post_handler(event)
        assert result["statusCode"] == 400

    def test_rejects_missing_project_id(self) -> None:
        from src.phases.api_handlers import pm_chat_post_handler

        event = {
            "pathParameters": {},
            "body": json.dumps({"message": "Hello"}),
        }
        result = pm_chat_post_handler(event)
        assert result["statusCode"] == 400


@pytest.mark.unit
class TestPmChatGetHandler:
    """Verify pm_chat_get_handler behavior."""

    @patch("src.phases.api_handlers.get_chat_history")
    def test_returns_chat_history(self, mock_history: MagicMock) -> None:
        from src.phases.api_handlers import pm_chat_get_handler
        from src.state.chat import ChatMessage

        mock_history.return_value = [
            ChatMessage(
                message_id="msg-1",
                role="customer",
                content="Hello",
                timestamp="2025-01-01T00:00:00",
            ),
            ChatMessage(
                message_id="msg-2",
                role="pm",
                content="Hi there",
                timestamp="2025-01-01T00:00:01",
            ),
        ]

        event = {"pathParameters": {"id": "proj-1"}, "queryStringParameters": None}
        result = pm_chat_get_handler(event)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["project_id"] == "proj-1"
        assert len(body["messages"]) == 2
        assert body["messages"][0]["role"] == "customer"
        assert body["messages"][1]["role"] == "pm"
        mock_history.assert_called_once_with("cloudcrew-projects", "proj-1", limit=50)

    @patch("src.phases.api_handlers.get_chat_history")
    def test_respects_limit_param(self, mock_history: MagicMock) -> None:
        from src.phases.api_handlers import pm_chat_get_handler

        mock_history.return_value = []

        event = {
            "pathParameters": {"id": "proj-1"},
            "queryStringParameters": {"limit": "10"},
        }
        pm_chat_get_handler(event)

        mock_history.assert_called_once_with("cloudcrew-projects", "proj-1", limit=10)

    def test_rejects_missing_project_id(self) -> None:
        from src.phases.api_handlers import pm_chat_get_handler

        event = {"pathParameters": {}, "queryStringParameters": None}
        result = pm_chat_get_handler(event)
        assert result["statusCode"] == 400

    @patch("src.phases.api_handlers.get_chat_history")
    def test_handles_invalid_limit(self, mock_history: MagicMock) -> None:
        from src.phases.api_handlers import pm_chat_get_handler

        mock_history.return_value = []

        event = {
            "pathParameters": {"id": "proj-1"},
            "queryStringParameters": {"limit": "abc"},
        }
        result = pm_chat_get_handler(event)

        # Invalid limit defaults to 50
        assert result["statusCode"] == 200
        mock_history.assert_called_once_with("cloudcrew-projects", "proj-1", limit=50)


@pytest.mark.unit
class TestUploadUrlHandler:
    """Verify upload_url_handler behavior."""

    @patch("src.phases.api_handlers.SOW_BUCKET", "my-bucket")
    @patch("src.phases.api_handlers.boto3")
    def test_returns_presigned_url(self, mock_boto3: MagicMock) -> None:
        from src.phases.api_handlers import upload_url_handler

        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = "https://s3.example.com/upload"
        mock_boto3.client.return_value = mock_s3

        event = {
            "pathParameters": {"id": "proj-1"},
            "body": json.dumps(
                {
                    "filename": "design.pdf",
                    "content_type": "application/pdf",
                }
            ),
        }
        result = upload_url_handler(event)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["upload_url"] == "https://s3.example.com/upload"
        assert body["filename"] == "design.pdf"
        assert "key" in body
        assert body["key"].startswith("projects/proj-1/uploads/")

        # Verify S3 client called correctly
        mock_s3.generate_presigned_url.assert_called_once()
        call_kwargs = mock_s3.generate_presigned_url.call_args
        params = call_kwargs[1]["Params"] if "Params" in call_kwargs[1] else call_kwargs[0][1]
        assert params["Bucket"] == "my-bucket"
        assert params["ContentType"] == "application/pdf"

    def test_rejects_missing_filename(self) -> None:
        from src.phases.api_handlers import upload_url_handler

        event = {
            "pathParameters": {"id": "proj-1"},
            "body": json.dumps({}),
        }
        result = upload_url_handler(event)
        assert result["statusCode"] == 400

    @patch("src.phases.api_handlers.SOW_BUCKET", "")
    def test_503_when_bucket_not_configured(self) -> None:
        from src.phases.api_handlers import upload_url_handler

        event = {
            "pathParameters": {"id": "proj-1"},
            "body": json.dumps({"filename": "test.pdf"}),
        }
        result = upload_url_handler(event)
        assert result["statusCode"] == 503

    def test_rejects_missing_project_id(self) -> None:
        from src.phases.api_handlers import upload_url_handler

        event = {
            "pathParameters": {},
            "body": json.dumps({"filename": "test.pdf"}),
        }
        result = upload_url_handler(event)
        assert result["statusCode"] == 400


@pytest.mark.unit
class TestBoardTasksHandler:
    """Verify board_tasks_handler behavior."""

    @patch("src.phases.api_handlers.list_tasks")
    def test_returns_tasks(self, mock_list: MagicMock) -> None:
        from src.phases.api_handlers import board_tasks_handler

        mock_list.return_value = [
            {"task_id": "t1", "title": "Research auth", "status": "done"},
            {"task_id": "t2", "title": "Implement auth", "status": "in_progress"},
        ]

        event = {"pathParameters": {"id": "proj-1"}}
        result = board_tasks_handler(event)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["project_id"] == "proj-1"
        assert len(body["tasks"]) == 2
        assert body["tasks"][0]["task_id"] == "t1"
        mock_list.assert_called_once_with("cloudcrew-board-tasks", "proj-1", phase="")

    @patch("src.phases.api_handlers.list_tasks")
    def test_returns_empty_list(self, mock_list: MagicMock) -> None:
        from src.phases.api_handlers import board_tasks_handler

        mock_list.return_value = []

        event = {"pathParameters": {"id": "proj-1"}}
        result = board_tasks_handler(event)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["tasks"] == []

    def test_rejects_missing_project_id(self) -> None:
        from src.phases.api_handlers import board_tasks_handler

        event = {"pathParameters": {}}
        result = board_tasks_handler(event)
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

    @patch("src.phases.api_handlers.pm_chat_post_handler")
    def test_routes_post_chat(self, mock_handler: MagicMock) -> None:
        from src.phases.api_handlers import route

        mock_handler.return_value = {"statusCode": 202, "body": "{}"}
        event = {"httpMethod": "POST", "resource": "/projects/{id}/chat"}
        route(event, None)
        mock_handler.assert_called_once_with(event)

    @patch("src.phases.api_handlers.pm_chat_get_handler")
    def test_routes_get_chat(self, mock_handler: MagicMock) -> None:
        from src.phases.api_handlers import route

        mock_handler.return_value = {"statusCode": 200, "body": "{}"}
        event = {"httpMethod": "GET", "resource": "/projects/{id}/chat"}
        route(event, None)
        mock_handler.assert_called_once_with(event)

    @patch("src.phases.api_handlers.upload_url_handler")
    def test_routes_post_upload(self, mock_handler: MagicMock) -> None:
        from src.phases.api_handlers import route

        mock_handler.return_value = {"statusCode": 200, "body": "{}"}
        event = {"httpMethod": "POST", "resource": "/projects/{id}/upload"}
        route(event, None)
        mock_handler.assert_called_once_with(event)

    @patch("src.phases.api_handlers.board_tasks_handler")
    def test_routes_get_tasks(self, mock_handler: MagicMock) -> None:
        from src.phases.api_handlers import route

        mock_handler.return_value = {"statusCode": 200, "body": "{}"}
        event = {"httpMethod": "GET", "resource": "/projects/{id}/tasks"}
        route(event, None)
        mock_handler.assert_called_once_with(event)

    def test_returns_404_for_unknown_route(self) -> None:
        from src.phases.api_handlers import route

        event = {"httpMethod": "DELETE", "resource": "/unknown"}
        result = route(event, None)
        assert result["statusCode"] == 404
