"""Task API handler for fetching board tasks.

Separated from api_handlers.py to keep file size under 500 lines.
"""

import logging
from typing import Any

from src.config import BOARD_TASKS_TABLE
from src.phases.auth_utils import api_response, verify_project_access
from src.state.tasks import list_tasks

logger = logging.getLogger(__name__)


def board_tasks_handler(event: dict[str, Any]) -> dict[str, Any]:
    """Get board tasks for a project, optionally filtered by phase.

    GET /projects/{id}/tasks?phase=ARCHITECTURE
    """
    project_id = event.get("pathParameters", {}).get("id", "")
    if not project_id:
        return api_response(400, {"error": "project_id is required"})

    # Verify user has access to this project
    is_authorized, _ = verify_project_access(event, project_id)
    if not is_authorized:
        logger.warning("Unauthorized tasks access for project=%s", project_id)
        return api_response(403, {"error": "Forbidden"})

    params = event.get("queryStringParameters") or {}
    phase_filter: str = params.get("phase", "")

    tasks = list_tasks(BOARD_TASKS_TABLE, project_id, phase=phase_filter)
    return api_response(200, {"project_id": project_id, "tasks": tasks})
