"""DynamoDB operations for PM chat message history.

Stores chat messages between the customer and PM agent. Messages use the
existing cloudcrew-projects table with a ``CHAT#`` sort key prefix.

This module imports from config — NEVER from agents/, tools/, or phases/.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import boto3

from src.config import AWS_REGION

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """A single chat message."""

    message_id: str
    role: str  # "customer" | "pm"
    content: str
    timestamp: str


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()


def _get_table(table_name: str) -> Any:
    """Get a DynamoDB Table resource."""
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return dynamodb.Table(table_name)


def store_chat_message(
    table_name: str,
    project_id: str,
    message_id: str,
    role: str,
    content: str,
    timestamp: str = "",
) -> ChatMessage:
    """Store a chat message in DynamoDB.

    Args:
        table_name: DynamoDB table name (cloudcrew-projects).
        project_id: The project identifier.
        message_id: Unique message ID.
        role: Message author — ``"customer"`` or ``"pm"``.
        content: Message text.
        timestamp: ISO 8601 timestamp (defaults to now).

    Returns:
        The persisted ChatMessage.
    """
    if not timestamp:
        timestamp = _now_iso()

    table = _get_table(table_name)
    table.put_item(
        Item={
            "PK": f"PROJECT#{project_id}",
            "SK": f"CHAT#{timestamp}#{message_id}",
            "message_id": message_id,
            "role": role,
            "content": content,
            "timestamp": timestamp,
        },
    )
    logger.debug(
        "Stored chat message %s (role=%s) for project %s",
        message_id,
        role,
        project_id,
    )
    return ChatMessage(
        message_id=message_id,
        role=role,
        content=content,
        timestamp=timestamp,
    )


def get_chat_history(
    table_name: str,
    project_id: str,
    limit: int = 50,
) -> list[ChatMessage]:
    """Query recent chat messages for a project.

    Returns messages in chronological order (oldest first).

    Args:
        table_name: DynamoDB table name.
        project_id: The project identifier.
        limit: Maximum number of messages to return.

    Returns:
        List of ChatMessage instances ordered by timestamp ascending.
    """
    table = _get_table(table_name)

    # Query in reverse to get the *latest* N messages …
    response = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :prefix)",
        ExpressionAttributeValues={
            ":pk": f"PROJECT#{project_id}",
            ":prefix": "CHAT#",
        },
        ScanIndexForward=False,
        Limit=limit,
    )

    items = response.get("Items", [])

    # … then reverse so the caller sees chronological order.
    items.reverse()

    return [
        ChatMessage(
            message_id=item.get("message_id", ""),
            role=item.get("role", ""),
            content=item.get("content", ""),
            timestamp=item.get("timestamp", ""),
        )
        for item in items
    ]


def chat_history_to_prompt(messages: list[ChatMessage]) -> str:
    """Format chat history as a text prompt for the PM agent.

    Args:
        messages: List of ChatMessage instances.

    Returns:
        Human-readable conversation transcript.
    """
    if not messages:
        return "(No previous messages.)"

    lines: list[str] = []
    for msg in messages:
        label = "Customer" if msg.role == "customer" else "PM"
        lines.append(f"[{label}]: {msg.content}")
    return "\n".join(lines)


def new_message_id() -> str:
    """Generate a unique message ID."""
    return str(uuid.uuid4())
