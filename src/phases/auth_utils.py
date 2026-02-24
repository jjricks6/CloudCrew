"""Authorization and response utilities for API handlers."""

import json
import logging
import time
from typing import Any

import boto3

from src.config import (
    CORS_ALLOWED_ORIGINS,
    CORS_MAX_AGE,
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_REQUESTS_PER_MINUTE,
    RATE_LIMIT_TABLE,
    TASK_LEDGER_TABLE,
)
from src.state.ledger import read_ledger

logger = logging.getLogger(__name__)


def _get_cors_origin() -> str:
    """Get CORS origin header value.

    Returns the configured CORS_ALLOWED_ORIGINS, which can be:
    - "*" for allow-all (default, less secure)
    - Single origin like "https://dashboard.example.com"
    - Multiple comma-separated origins (use first one for response)
    """
    origins = CORS_ALLOWED_ORIGINS.split(",")[0].strip()
    return origins if origins else "*"


def get_user_id_from_event(event: dict[str, Any]) -> str | None:
    """Extract user ID from Cognito claims in the Lambda event.

    Args:
        event: API Gateway Lambda proxy event with Cognito claims.

    Returns:
        The Cognito subject (unique user ID) or None if not found.
    """
    request_context = event.get("requestContext", {})
    authorizer = request_context.get("authorizer", {})
    claims = authorizer.get("claims", {})
    return claims.get("sub")  # type: ignore[no-any-return]


def verify_project_access(
    event: dict[str, Any],
    project_id: str,
) -> tuple[bool, str | None]:
    """Verify that the authenticated user has access to this project.

    Implementation: Project ownership model. Only the project owner can access it.

    Args:
        event: API Gateway Lambda proxy event.
        project_id: The project being accessed.

    Returns:
        (is_authorized, user_id) tuple. is_authorized is True if user has access.
    """
    user_id = get_user_id_from_event(event)
    if not user_id:
        logger.warning("No user ID in request")
        return False, None

    try:
        # Read project ledger and verify owner matches authenticated user
        ledger = read_ledger(TASK_LEDGER_TABLE, project_id)

        # Verify user is the project owner
        if ledger.owner_id != user_id:
            logger.warning(
                "Access denied: user=%s attempted to access project=%s owned by %s",
                user_id,
                project_id,
                ledger.owner_id,
            )
            return False, user_id

        logger.info("Project access verified for user=%s, project=%s", user_id, project_id)
        return True, user_id
    except Exception as exc:
        logger.warning("Project access check failed for project=%s: %s", project_id, exc)
        return False, None


def api_response(status_code: int, body: Any) -> dict[str, Any]:
    """Build an API Gateway proxy response with CORS headers.

    CORS headers are configured via environment variables:
    - CORS_ALLOWED_ORIGINS: comma-separated list or "*" (default: "*")
    - CORS_MAX_AGE: preflight cache duration in seconds (default: 86400)
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": _get_cors_origin(),
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
            "Access-Control-Max-Age": CORS_MAX_AGE,
            "Access-Control-Allow-Credentials": "true",
        },
        "body": json.dumps(body) if not isinstance(body, str) else body,
    }


def handle_cors_preflight(origin: str | None = None) -> dict[str, Any]:
    """Handle CORS preflight OPTIONS requests.

    Args:
        origin: Optional origin to validate (unused in allow-all mode).

    Returns:
        API Gateway response for OPTIONS request.
    """
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": _get_cors_origin(),
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
            "Access-Control-Max-Age": CORS_MAX_AGE,
            "Access-Control-Allow-Credentials": "true",
        },
        "body": "",
    }


def check_rate_limit(user_id: str | None) -> tuple[bool, str | None]:
    """Check if user has exceeded rate limit.

    Implementation: Per-user rate limiting using DynamoDB. Tracks request count
    per minute. Uses minute-based keys with TTL for automatic cleanup.

    Args:
        user_id: Cognito user ID, or None for unauthenticated requests.

    Returns:
        (is_allowed, error_message) tuple.
        - is_allowed is True if request is allowed
        - error_message is None if allowed, otherwise describes the limit
    """
    if not RATE_LIMIT_ENABLED or not user_id:
        return True, None

    try:
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(RATE_LIMIT_TABLE)

        # Create a key for the current minute
        current_minute = int(time.time()) // 60
        rate_limit_key = f"user#{user_id}#minute#{current_minute}"

        # Increment request count for this minute
        response = table.update_item(
            Key={"rate_limit_key": rate_limit_key},
            UpdateExpression="ADD request_count :inc SET #ttl = :ttl",
            ExpressionAttributeNames={"#ttl": "ttl"},
            ExpressionAttributeValues={
                ":inc": 1,
                ":ttl": current_minute * 60 + 120,  # Expire 2 minutes after minute ends
            },
            ReturnValues="ALL_NEW",
        )

        request_count = int(response["Attributes"]["request_count"])  # type: ignore[arg-type]

        if request_count > RATE_LIMIT_REQUESTS_PER_MINUTE:
            logger.warning(
                "Rate limit exceeded: user=%s, count=%d, limit=%d",
                user_id,
                request_count,
                RATE_LIMIT_REQUESTS_PER_MINUTE,
            )
            return False, f"Rate limit exceeded: {RATE_LIMIT_REQUESTS_PER_MINUTE} requests per minute"

        return True, None
    except Exception as exc:
        # On error, allow request but log warning
        logger.warning("Rate limit check failed for user=%s: %s", user_id, exc)
        return True, None
