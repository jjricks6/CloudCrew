"""Artifact content API handler for project artifacts.

Provides endpoint to fetch artifact file contents from project repository
for preview and download in the dashboard.
"""

import logging
from pathlib import Path
from typing import Any

import git

from src.config import PROJECT_REPO_PATH
from src.phases.auth_utils import api_response, verify_project_access

logger = logging.getLogger(__name__)


def artifact_content_handler(event: dict[str, Any]) -> dict[str, Any]:
    """Fetch artifact file content from project repository.

    GET /projects/{id}/artifacts?path={file_path}

    Returns artifact content for preview. Validates path to prevent directory traversal.
    Allowed paths must start with: docs/, security/, infra/, app/, data/

    Query parameters:
        path: Relative path to artifact file (required)

    Response:
        {
            "path": str,
            "content": str,
            "exists": bool
        }
    """
    project_id = event.get("pathParameters", {}).get("id", "")
    if not project_id:
        return api_response(400, {"error": "project_id is required"})

    # Verify user has access to this project
    is_authorized, _ = verify_project_access(event, project_id)
    if not is_authorized:
        logger.warning("Unauthorized artifact access for project=%s", project_id)
        return api_response(403, {"error": "Forbidden"})

    params = event.get("queryStringParameters") or {}
    file_path: str = params.get("path", "")

    if not file_path:
        return api_response(400, {"error": "path query parameter is required"})

    # Validate path starts with allowed prefixes
    allowed_prefixes = ("docs/", "security/", "infra/", "app/", "data/")
    if not any(file_path.startswith(prefix) for prefix in allowed_prefixes):
        return api_response(403, {"error": "Access denied to this path"})

    try:
        if not PROJECT_REPO_PATH:
            return api_response(503, {"error": "Project repository not configured"})

        repo = git.Repo(PROJECT_REPO_PATH)
        repo_root = Path(repo.working_dir)

        # Resolve path and check it doesn't escape repo
        resolved = (repo_root / file_path).resolve()
        if not str(resolved).startswith(str(repo_root.resolve())):
            return api_response(403, {"error": "Path traversal not allowed"})

        if not resolved.exists():
            return api_response(200, {"path": file_path, "exists": False, "content": ""})

        if not resolved.is_file():
            return api_response(400, {"error": "Path is not a file"})

        content = resolved.read_text()
        logger.info("artifact_content_handler: fetched %s", file_path)
        return api_response(200, {"path": file_path, "content": content, "exists": True})

    except Exception as exc:
        logger.exception("artifact_content_handler error: %s", exc)
        return api_response(500, {"error": f"Failed to fetch artifact: {exc}"})
