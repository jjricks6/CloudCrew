"""Artifact API handlers for project documentation artifacts.

Provides endpoints to list and fetch documentation artifact contents from S3.
Only docs/ and security/ artifacts are synced to S3 by the ECS phase runner.
Code artifacts (infra/, app/, data/) live exclusively in the customer's GitHub repo.
"""

import logging
from pathlib import PurePosixPath
from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.config import AWS_REGION, SOW_BUCKET
from src.phases.auth_utils import api_response, verify_project_access

logger = logging.getLogger(__name__)

ALLOWED_PREFIXES = ("docs/", "security/")


def _path_to_display_name(rel_path: str) -> str:
    """Derive a human-readable display name from a file path.

    Examples:
        docs/architecture/system-design.md  -> System Design
        security/threat_model.md            -> Threat Model
        docs/phase-summaries/architecture.md -> Phase Summary
    """
    # Phase summaries get a special label
    if rel_path.startswith("docs/phase-summaries/"):
        return "Phase Summary"

    filename = PurePosixPath(rel_path).stem
    name = filename.replace("-", " ").replace("_", " ")
    return name.title()


def artifact_content_handler(event: dict[str, Any]) -> dict[str, Any]:
    """List or fetch artifact files from S3.

    GET /projects/{id}/artifacts?action=list
        List all artifact files for this project.

    GET /projects/{id}/artifacts?path={file_path}
        Fetch content of a specific artifact file.

    Validates paths to prevent directory traversal.
    Allowed paths must start with: docs/, security/

    Query parameters:
        action: Set to "list" to list all artifacts (optional)
        path: Relative path to artifact file (required unless action=list)

    Response (list mode):
        {
            "artifacts": [
                {"name": str, "path": str},
                ...
            ]
        }

    Response (content mode):
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
    action: str = params.get("action", "")

    if action == "list":
        return _list_artifacts(project_id)

    return _get_artifact_content(project_id, params)


def _list_artifacts(project_id: str) -> dict[str, Any]:
    """List all artifact files for a project from S3."""
    if not SOW_BUCKET:
        return api_response(503, {"error": "Artifact storage not configured"})

    prefix = f"projects/{project_id}/artifacts/"
    prefix_len = len(prefix)

    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        artifacts: list[dict[str, str]] = []
        paginator = s3.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=SOW_BUCKET, Prefix=prefix):
            for obj in page.get("Contents", []):
                rel_path = obj["Key"][prefix_len:]
                # Only include files under allowed prefixes
                if not any(rel_path.startswith(p) for p in ALLOWED_PREFIXES):
                    continue
                artifacts.append(
                    {
                        "name": _path_to_display_name(rel_path),
                        "path": rel_path,
                    }
                )

        # Sort: phase summary first, then alphabetically by path
        artifacts.sort(key=lambda a: (0 if a["name"] == "Phase Summary" else 1, a["path"]))

        logger.info(
            "artifact_list: found %d artifacts for project=%s",
            len(artifacts),
            project_id,
        )
        return api_response(200, {"artifacts": artifacts})

    except ClientError as exc:
        logger.exception("artifact_list S3 error: %s", exc)
        return api_response(500, {"error": f"Failed to list artifacts: {exc}"})

    except Exception as exc:
        logger.exception("artifact_list error: %s", exc)
        return api_response(500, {"error": f"Failed to list artifacts: {exc}"})


def _get_artifact_content(
    project_id: str,
    params: dict[str, str],
) -> dict[str, Any]:
    """Fetch content of a single artifact file from S3."""
    file_path: str = params.get("path", "")

    if not file_path:
        return api_response(400, {"error": "path query parameter is required"})

    if not any(file_path.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        return api_response(403, {"error": "Access denied to this path"})

    # Reject path traversal attempts
    if ".." in file_path:
        return api_response(403, {"error": "Path traversal not allowed"})

    if not SOW_BUCKET:
        return api_response(503, {"error": "Artifact storage not configured"})

    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        s3_key = f"projects/{project_id}/artifacts/{file_path}"
        response = s3.get_object(Bucket=SOW_BUCKET, Key=s3_key)
        content = response["Body"].read().decode("utf-8")
        logger.info("artifact_content: fetched %s from S3", file_path)
        return api_response(200, {"path": file_path, "content": content, "exists": True})

    except ClientError as exc:
        if exc.response["Error"]["Code"] == "NoSuchKey":
            return api_response(200, {"path": file_path, "exists": False, "content": ""})
        logger.exception("artifact_content S3 error: %s", exc)
        return api_response(500, {"error": f"Failed to fetch artifact: {exc}"})

    except Exception as exc:
        logger.exception("artifact_content error: %s", exc)
        return api_response(500, {"error": f"Failed to fetch artifact: {exc}"})
