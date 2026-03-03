"""Tests for src/phases/task_handlers.py."""

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

TEST_USER_ID = "test-user-123"


def _create_event(
    project_id: str = "proj-1",
    query_params: dict[str, str] | None = None,
    user_id: str = TEST_USER_ID,
) -> dict[str, Any]:
    """Create an API Gateway Lambda event with Cognito claims."""
    event: dict[str, Any] = {
        "pathParameters": {"id": project_id},
        "requestContext": {
            "authorizer": {
                "claims": {"sub": user_id},
            }
        },
    }
    if query_params is not None:
        event["queryStringParameters"] = query_params
    return event


@pytest.mark.unit
class TestBoardTasksHandler:
    """Verify board_tasks_handler behaviour."""

    @patch("src.phases.task_handlers.list_tasks")
    @patch("src.phases.task_handlers.verify_project_access", return_value=(True, TEST_USER_ID))
    def test_returns_tasks(self, _mock_auth: MagicMock, mock_list: MagicMock) -> None:
        from src.phases.task_handlers import board_tasks_handler

        mock_list.return_value = [{"task_id": "t1", "title": "Design API"}]
        event = _create_event()
        result = board_tasks_handler(event)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["project_id"] == "proj-1"
        assert len(body["tasks"]) == 1
        mock_list.assert_called_once()

    @patch("src.phases.task_handlers.list_tasks")
    @patch("src.phases.task_handlers.verify_project_access", return_value=(True, TEST_USER_ID))
    def test_filters_by_phase(self, _mock_auth: MagicMock, mock_list: MagicMock) -> None:
        from src.phases.task_handlers import board_tasks_handler

        mock_list.return_value = []
        event = _create_event(query_params={"phase": "ARCHITECTURE"})
        board_tasks_handler(event)

        _, kwargs = mock_list.call_args
        assert kwargs.get("phase") == "ARCHITECTURE" or mock_list.call_args.args[2] == "ARCHITECTURE"

    @patch("src.phases.task_handlers.verify_project_access", return_value=(False, None))
    def test_returns_403_when_unauthorized(self, _mock_auth: MagicMock) -> None:
        from src.phases.task_handlers import board_tasks_handler

        event = _create_event()
        result = board_tasks_handler(event)

        assert result["statusCode"] == 403

    def test_returns_400_when_no_project_id(self) -> None:
        from src.phases.task_handlers import board_tasks_handler

        event: dict[str, Any] = {
            "pathParameters": {},
            "requestContext": {"authorizer": {"claims": {"sub": TEST_USER_ID}}},
        }
        result = board_tasks_handler(event)

        assert result["statusCode"] == 400

    @patch("src.phases.task_handlers.list_tasks")
    @patch("src.phases.task_handlers.verify_project_access", return_value=(True, TEST_USER_ID))
    def test_handles_missing_query_params(self, _mock_auth: MagicMock, mock_list: MagicMock) -> None:
        from src.phases.task_handlers import board_tasks_handler

        mock_list.return_value = []
        event = _create_event()
        # No queryStringParameters key at all
        result = board_tasks_handler(event)

        assert result["statusCode"] == 200
