"""Shared pytest fixtures for CloudCrew tests.

Centralises constants and factory helpers that are duplicated across
multiple test modules (api_handlers, task_handlers, artifact_handlers,
auth_utils, middleware).
"""

import json
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_USER_ID = "test-user-123"
TEST_PROJECT_ID = "proj-1"


# ---------------------------------------------------------------------------
# Factory helpers (exposed as fixtures for convenience)
# ---------------------------------------------------------------------------


def make_apigw_event(
    path_params: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    query_params: dict[str, str] | None = None,
    user_id: str = TEST_USER_ID,
) -> dict[str, Any]:
    """Create an API Gateway Lambda proxy event with Cognito claims.

    This is the canonical builder for Lambda handler test events.
    """
    event: dict[str, Any] = {
        "pathParameters": path_params or {},
        "requestContext": {
            "authorizer": {
                "claims": {"sub": user_id},
            }
        },
    }
    if body is not None:
        event["body"] = json.dumps(body)
    if query_params is not None:
        event["queryStringParameters"] = query_params
    return event


@pytest.fixture()
def apigw_event_factory():
    """Pytest fixture that returns the ``make_apigw_event`` factory."""
    return make_apigw_event
