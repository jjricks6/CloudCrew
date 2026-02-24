"""Tests for src/phases/middleware.py."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest


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
class TestApplyMiddleware:
    """Verify middleware behavior."""

    @patch("src.phases.middleware.check_rate_limit")
    def test_allows_request_when_rate_limit_ok(self, mock_limit: MagicMock) -> None:
        from src.phases.middleware import apply_middleware

        mock_limit.return_value = (True, None)
        event = _create_event_with_auth("user-123")

        should_continue, error_response = apply_middleware(event)

        assert should_continue is True
        assert error_response is None

    @patch("src.phases.middleware.check_rate_limit")
    def test_blocks_request_when_rate_limit_exceeded(self, mock_limit: MagicMock) -> None:
        from src.phases.middleware import apply_middleware

        mock_limit.return_value = (False, "Rate limit exceeded: 100 requests per minute")
        event = _create_event_with_auth("user-123")

        should_continue, error_response = apply_middleware(event)

        assert should_continue is False
        assert error_response is not None
        assert error_response["statusCode"] == 429
        assert "Rate limit exceeded" in error_response["body"]
