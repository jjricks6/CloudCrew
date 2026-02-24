"""API middleware for cross-cutting concerns (rate limiting, CORS, etc.)."""

import logging
from typing import Any

from src.phases.auth_utils import api_response, check_rate_limit, get_user_id_from_event

logger = logging.getLogger(__name__)


def apply_middleware(
    event: dict[str, Any],
) -> tuple[bool, dict[str, Any] | None]:
    """Apply middleware checks to incoming request.

    Args:
        event: API Gateway proxy event.

    Returns:
        (should_continue, error_response) tuple.
        - should_continue is True if request should proceed
        - error_response is None if no error, otherwise an API error response
    """
    # Check rate limit for authenticated users
    user_id = get_user_id_from_event(event)
    is_allowed, error_message = check_rate_limit(user_id)
    if not is_allowed:
        logger.warning("Rate limit exceeded for user=%s", user_id)
        return False, api_response(429, {"error": error_message})

    return True, None
