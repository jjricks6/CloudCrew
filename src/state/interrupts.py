"""DynamoDB operations for mid-phase interrupt records.

Stores interrupt questions raised by agents and retrieves customer
responses. The ECS phase runner polls for responses; the API handler
writes them.

Supports a special ``sow_review:`` prefix in the question field. When
detected, the module broadcasts a ``sow_review`` WebSocket event instead
of the generic ``interrupt_raised`` event so the dashboard can show a
deterministic SOW review card.

This module imports from config — NEVER from agents/, tools/, or phases/.
"""

import logging
from datetime import UTC, datetime
from typing import Any

import boto3

from src.config import AWS_REGION
from src.state.broadcast import broadcast_to_project

logger = logging.getLogger(__name__)

# Prefix set by CustomerInterruptHook for SOW review interrupts.
SOW_REVIEW_PREFIX = "sow_review:"


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()


def _get_table(table_name: str) -> Any:
    """Get a DynamoDB Table resource."""
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return dynamodb.Table(table_name)


def store_interrupt(
    table_name: str,
    project_id: str,
    interrupt_id: str,
    question: str,
    phase: str = "",
    sow_content: str = "",
) -> None:
    """Store an interrupt question for a customer to answer.

    Args:
        table_name: DynamoDB table name.
        project_id: The project identifier.
        interrupt_id: Unique identifier for this interrupt.
        question: The question text for the customer.
        phase: Current delivery phase name.
        sow_content: SOW markdown content for sow_review interrupts.
    """
    table = _get_table(table_name)
    table.put_item(
        Item={
            "PK": f"PROJECT#{project_id}",
            "SK": f"INTERRUPT#{interrupt_id}",
            "interrupt_id": interrupt_id,
            "question": question,
            "response": "",
            "status": "PENDING",
            "created_at": _now_iso(),
            "answered_at": "",
        },
    )
    logger.info("Stored interrupt %s for project %s", interrupt_id, project_id)

    # Broadcast event to connected dashboard clients.
    # SOW review interrupts get a dedicated event type so the dashboard
    # can show the SOW review card deterministically (no text matching).
    if question.startswith(SOW_REVIEW_PREFIX):
        msg: dict[str, str] = {
            "event": "sow_review",
            "project_id": project_id,
            "phase": phase,
            "interrupt_id": interrupt_id,
        }
        if sow_content:
            msg["sow_content"] = sow_content
        broadcast_to_project(project_id, msg)
    else:
        broadcast_to_project(
            project_id,
            {
                "event": "interrupt_raised",
                "project_id": project_id,
                "phase": phase,
                "interrupt_id": interrupt_id,
                "question": question,
            },
        )


def get_interrupt_response(
    table_name: str,
    project_id: str,
    interrupt_id: str,
) -> str:
    """Check if a customer has responded to an interrupt.

    Args:
        table_name: DynamoDB table name.
        project_id: The project identifier.
        interrupt_id: The interrupt to check.

    Returns:
        The response text if answered, or empty string if still pending.
    """
    table = _get_table(table_name)
    response = table.get_item(
        Key={
            "PK": f"PROJECT#{project_id}",
            "SK": f"INTERRUPT#{interrupt_id}",
        },
    )
    item = response.get("Item")
    if not item:
        logger.warning("Interrupt %s not found for project %s", interrupt_id, project_id)
        return ""
    if item.get("status") != "ANSWERED":
        return ""
    return str(item.get("response", ""))


def store_interrupt_response(
    table_name: str,
    project_id: str,
    interrupt_id: str,
    response: str,
) -> None:
    """Store a customer's response to an interrupt.

    Args:
        table_name: DynamoDB table name.
        project_id: The project identifier.
        interrupt_id: The interrupt being answered.
        response: The customer's response text.
    """
    table = _get_table(table_name)
    table.update_item(
        Key={
            "PK": f"PROJECT#{project_id}",
            "SK": f"INTERRUPT#{interrupt_id}",
        },
        UpdateExpression="SET #resp = :resp, #status = :status, answered_at = :ts",
        ExpressionAttributeNames={
            "#resp": "response",
            "#status": "status",
        },
        ExpressionAttributeValues={
            ":resp": response,
            ":status": "ANSWERED",
            ":ts": _now_iso(),
        },
    )
    logger.info("Stored response for interrupt %s, project %s", interrupt_id, project_id)

    # Broadcast interrupt_answered event so the dashboard knows to resume
    broadcast_to_project(
        project_id,
        {
            "event": "interrupt_answered",
            "project_id": project_id,
            "interrupt_id": interrupt_id,
        },
    )
