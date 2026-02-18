"""DynamoDB operations for Step Functions approval task tokens.

Stores and retrieves waitForTaskToken tokens so that the customer API
can send approval/revision decisions back to Step Functions.

This module imports from config — NEVER from agents/, tools/, or phases/.
"""

import logging
from datetime import UTC, datetime
from typing import Any

import boto3

from src.config import AWS_REGION

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()


def _get_table(table_name: str) -> Any:
    """Get a DynamoDB Table resource."""
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return dynamodb.Table(table_name)


def store_token(
    table_name: str,
    project_id: str,
    phase: str,
    task_token: str,
) -> None:
    """Store a Step Functions task token for later retrieval.

    Args:
        table_name: DynamoDB table name.
        project_id: The project identifier.
        phase: The phase awaiting approval.
        task_token: The Step Functions waitForTaskToken.
    """
    table = _get_table(table_name)
    table.put_item(
        Item={
            "PK": f"PROJECT#{project_id}",
            "SK": f"TOKEN#{phase}",
            "task_token": task_token,
            "phase": phase,
            "created_at": _now_iso(),
        },
    )
    logger.info("Stored approval token for project %s, phase %s", project_id, phase)


def get_token(table_name: str, project_id: str, phase: str) -> str:
    """Retrieve a stored task token.

    Args:
        table_name: DynamoDB table name.
        project_id: The project identifier.
        phase: The phase to get the token for.

    Returns:
        The task token string, or empty string if not found.
    """
    table = _get_table(table_name)
    response = table.get_item(
        Key={"PK": f"PROJECT#{project_id}", "SK": f"TOKEN#{phase}"},
    )
    item = response.get("Item")
    if not item:
        logger.warning("No token found for project %s, phase %s", project_id, phase)
        return ""
    return str(item.get("task_token", ""))


def delete_token(table_name: str, project_id: str, phase: str) -> None:
    """Delete a task token after it has been used.

    Args:
        table_name: DynamoDB table name.
        project_id: The project identifier.
        phase: The phase whose token to delete.
    """
    table = _get_table(table_name)
    table.delete_item(
        Key={"PK": f"PROJECT#{project_id}", "SK": f"TOKEN#{phase}"},
    )
    logger.info("Deleted approval token for project %s, phase %s", project_id, phase)
