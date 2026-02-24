"""Tests for src/phases/auth_utils.py."""

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from src.state.models import TaskLedger


def _create_event_with_auth(user_id: str = "test-user-123") -> dict[str, Any]:
    """Create an API Gateway Lambda event with Cognito claims."""
    return {
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": user_id,
                }
            }
        }
    }


@pytest.mark.unit
class TestGetUserIdFromEvent:
    """Verify get_user_id_from_event behavior."""

    def test_extracts_user_id(self) -> None:
        from src.phases.auth_utils import get_user_id_from_event

        event = _create_event_with_auth("user-123")
        user_id = get_user_id_from_event(event)
        assert user_id == "user-123"

    def test_returns_none_when_no_claims(self) -> None:
        from src.phases.auth_utils import get_user_id_from_event

        event = {"requestContext": {"authorizer": {}}}
        user_id = get_user_id_from_event(event)
        assert user_id is None

    def test_returns_none_when_no_sub(self) -> None:
        from src.phases.auth_utils import get_user_id_from_event

        event = {"requestContext": {"authorizer": {"claims": {}}}}
        user_id = get_user_id_from_event(event)
        assert user_id is None


@pytest.mark.unit
class TestVerifyProjectAccess:
    """Verify project ownership and access control."""

    @patch("src.phases.auth_utils.read_ledger")
    def test_allows_owner_access(self, mock_read: MagicMock) -> None:
        from src.phases.auth_utils import verify_project_access

        mock_read.return_value = TaskLedger(
            project_id="proj-1",
            owner_id="user-123",
        )

        event = _create_event_with_auth("user-123")
        is_authorized, user_id = verify_project_access(event, "proj-1")

        assert is_authorized is True
        assert user_id == "user-123"

    @patch("src.phases.auth_utils.read_ledger")
    def test_denies_non_owner_access(self, mock_read: MagicMock) -> None:
        from src.phases.auth_utils import verify_project_access

        mock_read.return_value = TaskLedger(
            project_id="proj-1",
            owner_id="owner-user-456",
        )

        event = _create_event_with_auth("attacker-user-789")
        is_authorized, user_id = verify_project_access(event, "proj-1")

        assert is_authorized is False
        assert user_id == "attacker-user-789"

    def test_denies_unauthenticated_access(self) -> None:
        from src.phases.auth_utils import verify_project_access

        event = {"requestContext": {"authorizer": {"claims": {}}}}
        is_authorized, user_id = verify_project_access(event, "proj-1")

        assert is_authorized is False
        assert user_id is None

    @patch("src.phases.auth_utils.read_ledger")
    def test_handles_missing_project(self, mock_read: MagicMock) -> None:
        from src.phases.auth_utils import verify_project_access

        mock_read.side_effect = Exception("Project not found")

        event = _create_event_with_auth("user-123")
        is_authorized, _ = verify_project_access(event, "proj-1")

        assert is_authorized is False


@pytest.mark.unit
class TestApiResponse:
    """Verify API response formatting."""

    def test_includes_cors_headers(self) -> None:
        from src.phases.auth_utils import api_response

        response = api_response(200, {"message": "OK"})

        assert response["statusCode"] == 200
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"
        assert response["headers"]["Content-Type"] == "application/json"
        assert response["headers"]["Access-Control-Allow-Methods"] == "GET,POST,PUT,DELETE,OPTIONS"

    def test_serializes_dict_to_json(self) -> None:
        from src.phases.auth_utils import api_response

        response = api_response(201, {"project_id": "proj-1"})

        body = json.loads(response["body"])
        assert body["project_id"] == "proj-1"

    def test_handles_string_body(self) -> None:
        from src.phases.auth_utils import api_response

        response = api_response(200, "plain text")

        assert response["body"] == "plain text"


@pytest.mark.unit
class TestCheckRateLimit:
    """Verify rate limiting behavior."""

    def test_allows_request_when_disabled(self) -> None:
        from src.phases.auth_utils import check_rate_limit

        with patch("src.phases.auth_utils.RATE_LIMIT_ENABLED", False):
            is_allowed, error_message = check_rate_limit("user-123")

            assert is_allowed is True
            assert error_message is None

    def test_allows_request_for_unauthenticated_user(self) -> None:
        from src.phases.auth_utils import check_rate_limit

        is_allowed, error_message = check_rate_limit(None)

        assert is_allowed is True
        assert error_message is None

    @patch("src.phases.auth_utils.boto3.resource")
    @patch("src.phases.auth_utils.RATE_LIMIT_ENABLED", True)
    def test_allows_request_under_limit(self, mock_boto: MagicMock) -> None:
        from src.phases.auth_utils import check_rate_limit

        mock_table = MagicMock()
        mock_table.update_item.return_value = {"Attributes": {"request_count": 50}}
        mock_resource = MagicMock()
        mock_resource.Table.return_value = mock_table
        mock_boto.return_value = mock_resource

        with patch("src.phases.auth_utils.RATE_LIMIT_REQUESTS_PER_MINUTE", 100):
            is_allowed, error_message = check_rate_limit("user-123")

            assert is_allowed is True
            assert error_message is None

    @patch("src.phases.auth_utils.boto3.resource")
    @patch("src.phases.auth_utils.RATE_LIMIT_ENABLED", True)
    def test_denies_request_over_limit(self, mock_boto: MagicMock) -> None:
        from src.phases.auth_utils import check_rate_limit

        mock_table = MagicMock()
        mock_table.update_item.return_value = {"Attributes": {"request_count": 101}}
        mock_resource = MagicMock()
        mock_resource.Table.return_value = mock_table
        mock_boto.return_value = mock_resource

        with patch("src.phases.auth_utils.RATE_LIMIT_REQUESTS_PER_MINUTE", 100):
            is_allowed, error_message = check_rate_limit("user-123")

            assert is_allowed is False
            assert "Rate limit exceeded" in error_message  # type: ignore

    @patch("src.phases.auth_utils.boto3.resource")
    @patch("src.phases.auth_utils.RATE_LIMIT_ENABLED", True)
    def test_allows_on_dynamodb_error(self, mock_boto: MagicMock) -> None:
        from src.phases.auth_utils import check_rate_limit

        mock_table = MagicMock()
        mock_table.update_item.side_effect = Exception("DynamoDB error")
        mock_resource = MagicMock()
        mock_resource.Table.return_value = mock_table
        mock_boto.return_value = mock_resource

        is_allowed, error_message = check_rate_limit("user-123")

        # On error, allow request but log warning
        assert is_allowed is True
        assert error_message is None
