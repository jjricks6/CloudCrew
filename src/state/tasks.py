"""DynamoDB operations for board tasks (kanban).

Agents create and update tasks during phase execution. Each write
broadcasts a WebSocket event so the dashboard updates in real-time.

Unlike activity events (24h TTL), board tasks are retained permanently
as project history. Cleanup should be handled at the project level
(delete all items for a project) rather than via DynamoDB TTL.

This module imports from config and state.broadcast — NEVER from agents/,
tools/, or phases/.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import boto3

from src.config import AWS_REGION
from src.state.broadcast import broadcast_to_project

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()


_INTERNAL_KEYS = {"PK", "SK"}

_dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)


def _strip_keys(item: dict[str, Any]) -> dict[str, Any]:
    """Remove DynamoDB composite keys (PK, SK) before returning to callers."""
    return {k: v for k, v in item.items() if k not in _INTERNAL_KEYS}


def _get_table(table_name: str) -> Any:
    """Get a DynamoDB Table resource."""
    return _dynamodb.Table(table_name)


def create_task(
    table_name: str,
    project_id: str,
    title: str,
    description: str,
    phase: str,
    assigned_to: str,
) -> dict[str, Any]:
    """Create a new board task.

    Args:
        table_name: DynamoDB table name for board tasks.
        project_id: The project identifier.
        title: Short title for the task.
        description: Detailed description of what needs to be done.
        phase: Delivery phase this task belongs to.
        assigned_to: Agent name responsible for the task.

    Returns:
        The created task as a dict.
    """
    task_id = str(uuid.uuid4())
    now = _now_iso()
    item: dict[str, Any] = {
        "PK": f"PROJECT#{project_id}",
        "SK": f"TASK#{phase}#{task_id}",
        "task_id": task_id,
        "title": title,
        "description": description,
        "phase": phase,
        "status": "backlog",
        "assigned_to": assigned_to,
        "comments": [],
        "artifact_path": "",
        "created_at": now,
        "updated_at": now,
    }

    table = _get_table(table_name)
    table.put_item(Item=item)
    logger.info("Created task %s for project %s phase %s", task_id, project_id, phase)

    broadcast_to_project(
        project_id,
        {
            "event": "task_created",
            "project_id": project_id,
            "phase": phase,
            "task_id": task_id,
            "title": title,
            "assigned_to": assigned_to,
        },
    )

    return _strip_keys(item)


def update_task(
    table_name: str,
    project_id: str,
    phase: str,
    task_id: str,
    updates: dict[str, Any],
) -> None:
    """Update fields on an existing board task.

    Args:
        table_name: DynamoDB table name for board tasks.
        project_id: The project identifier.
        phase: Delivery phase the task belongs to.
        task_id: The task to update.
        updates: Dict of field names to new values. Allowed fields:
            status, assigned_to, artifact_path, title, description.
    """
    allowed = {"status", "assigned_to", "artifact_path", "title", "description"}
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return

    # Build DynamoDB update expression — includes updated_at timestamp
    db_fields = {**filtered, "updated_at": _now_iso()}

    expr_parts: list[str] = []
    names: dict[str, str] = {}
    values: dict[str, Any] = {}
    for i, (key, val) in enumerate(db_fields.items()):
        alias = f"#f{i}"
        placeholder = f":v{i}"
        expr_parts.append(f"{alias} = {placeholder}")
        names[alias] = key
        values[placeholder] = val

    table = _get_table(table_name)
    table.update_item(
        Key={
            "PK": f"PROJECT#{project_id}",
            "SK": f"TASK#{phase}#{task_id}",
        },
        UpdateExpression="SET " + ", ".join(expr_parts),
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
    )
    logger.info("Updated task %s for project %s", task_id, project_id)

    # Broadcast only user-requested fields (not internal updated_at)
    broadcast_to_project(
        project_id,
        {
            "event": "task_updated",
            "project_id": project_id,
            "phase": phase,
            "task_id": task_id,
            "updates": filtered,
        },
    )


def add_comment(
    table_name: str,
    project_id: str,
    phase: str,
    task_id: str,
    author: str,
    content: str,
) -> None:
    """Add a comment to a board task.

    Args:
        table_name: DynamoDB table name for board tasks.
        project_id: The project identifier.
        phase: Delivery phase the task belongs to.
        task_id: The task to comment on.
        author: Agent name adding the comment.
        content: Comment text.
    """
    comment = {
        "author": author,
        "content": content,
        "timestamp": _now_iso(),
    }

    table = _get_table(table_name)
    table.update_item(
        Key={
            "PK": f"PROJECT#{project_id}",
            "SK": f"TASK#{phase}#{task_id}",
        },
        UpdateExpression="SET comments = list_append(comments, :c), updated_at = :ts",
        ExpressionAttributeValues={
            ":c": [comment],
            ":ts": _now_iso(),
        },
    )
    logger.info("Added comment to task %s by %s", task_id, author)

    broadcast_to_project(
        project_id,
        {
            "event": "task_updated",
            "project_id": project_id,
            "phase": phase,
            "task_id": task_id,
            "updates": {"comment_added": comment},
        },
    )


def list_tasks(
    table_name: str,
    project_id: str,
    phase: str = "",
) -> list[dict[str, Any]]:
    """List board tasks for a project, optionally filtered by phase.

    Args:
        table_name: DynamoDB table name for board tasks.
        project_id: The project identifier.
        phase: If provided, only return tasks for this phase.

    Returns:
        List of task dicts sorted by created_at (PK/SK keys stripped).
    """
    table = _get_table(table_name)
    sk_prefix = f"TASK#{phase}#" if phase else "TASK#"
    response = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :prefix)",
        ExpressionAttributeValues={
            ":pk": f"PROJECT#{project_id}",
            ":prefix": sk_prefix,
        },
    )
    items: list[dict[str, Any]] = response.get("Items", [])
    items.sort(key=lambda t: t.get("created_at", ""))
    return [_strip_keys(i) for i in items]


def get_task(
    table_name: str,
    project_id: str,
    phase: str,
    task_id: str,
) -> dict[str, Any] | None:
    """Get a single board task.

    Args:
        table_name: DynamoDB table name for board tasks.
        project_id: The project identifier.
        phase: Delivery phase the task belongs to.
        task_id: The task to retrieve.

    Returns:
        Task dict or None if not found.
    """
    table = _get_table(table_name)
    response = table.get_item(
        Key={
            "PK": f"PROJECT#{project_id}",
            "SK": f"TASK#{phase}#{task_id}",
        },
    )
    item: dict[str, Any] | None = response.get("Item")
    return _strip_keys(item) if item else None
