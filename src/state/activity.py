"""DynamoDB operations for agent activity events.

Stores real-time agent activity events for the customer dashboard.
Events have a 24-hour TTL and are queried for initial page load;
ongoing updates arrive via WebSocket.

This module imports from config — NEVER from agents/, tools/, or phases/.
"""

import logging
import uuid
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


def _ttl_24h() -> int:
    """Return a Unix timestamp 24 hours from now."""
    return int(datetime.now(UTC).timestamp()) + 86400


def store_activity_event(
    table_name: str,
    project_id: str,
    event_type: str,
    agent_name: str,
    phase: str,
    detail: str = "",
) -> dict[str, str]:
    """Store an agent activity event.

    Args:
        table_name: DynamoDB table name.
        project_id: The project identifier.
        event_type: Event type (agent_active, agent_idle, handoff, task_progress).
        agent_name: Name of the agent involved.
        phase: Current delivery phase.
        detail: Human-readable description of what happened.

    Returns:
        Dict with event_id and timestamp.
    """
    table = _get_table(table_name)
    timestamp = _now_iso()
    event_id = str(uuid.uuid4())

    table.put_item(
        Item={
            "PK": f"PROJECT#{project_id}",
            "SK": f"EVENT#{timestamp}#{event_id}",
            "event_id": event_id,
            "event_type": event_type,
            "agent_name": agent_name,
            "phase": phase,
            "detail": detail,
            "timestamp": timestamp,
            "ttl": _ttl_24h(),
        },
    )
    logger.debug(
        "Stored activity event %s for project %s: %s/%s",
        event_id,
        project_id,
        event_type,
        agent_name,
    )
    return {"event_id": event_id, "timestamp": timestamp}


def get_recent_activity(
    table_name: str,
    project_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Query recent activity events for a project.

    Returns events in reverse chronological order (newest first).

    Args:
        table_name: DynamoDB table name.
        project_id: The project identifier.
        limit: Maximum number of events to return.

    Returns:
        List of activity event dicts.
    """
    table = _get_table(table_name)
    response = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :prefix)",
        ExpressionAttributeValues={
            ":pk": f"PROJECT#{project_id}",
            ":prefix": "EVENT#",
        },
        ScanIndexForward=False,
        Limit=limit,
    )
    return [
        {
            "event_id": item.get("event_id", ""),
            "event_type": item.get("event_type", ""),
            "agent_name": item.get("agent_name", ""),
            "phase": item.get("phase", ""),
            "detail": item.get("detail", ""),
            "timestamp": item.get("timestamp", ""),
        }
        for item in response.get("Items", [])
    ]
