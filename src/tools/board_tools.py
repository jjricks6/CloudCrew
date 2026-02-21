"""Board task tools for the kanban board.

All agents get these tools to create tasks, update status, and add comments.
This module imports from state/ — NEVER from agents/.
"""

import json
import logging
from typing import Any

from strands import tool
from strands.types.tools import ToolContext

from src.state.tasks import add_comment, create_task, update_task

logger = logging.getLogger(__name__)


@tool(context=True)
def create_board_task(
    title: str,
    description: str,
    assigned_to: str,
    tool_context: ToolContext,
) -> str:
    """Create a new task on the kanban board.

    Use this at the start of a phase to plan work, or mid-phase when
    new problems arise. Tasks start in the "backlog" column.

    Args:
        title: Short title for the task (e.g. "Research authentication options").
        description: Detailed description of what needs to be done.
        assigned_to: Agent name responsible (e.g. "sa", "dev", "infra").
        tool_context: Strands tool context (injected by framework).

    Returns:
        Confirmation with the new task ID.
    """
    project_id = tool_context.invocation_state.get("project_id", "")
    table_name = tool_context.invocation_state.get("board_tasks_table", "")
    phase = tool_context.invocation_state.get("phase", "")

    if not project_id or not table_name:
        return "Error: project_id or board_tasks_table not set in invocation state."

    try:
        item = create_task(
            table_name=table_name,
            project_id=project_id,
            title=title,
            description=description,
            phase=phase,
            assigned_to=assigned_to,
        )
        return f"Created task '{title}' (ID: {item['task_id']}) assigned to {assigned_to}."
    except Exception as e:
        logger.exception("Failed to create board task for project %s", project_id)
        return f"Error creating task: {e}"


@tool(context=True)
def update_board_task(
    task_id: str,
    updates_json: str,
    tool_context: ToolContext,
) -> str:
    """Update a board task's status or other fields.

    Use this to move tasks between columns (backlog → in_progress →
    review → done), reassign them, or link an artifact.

    Args:
        task_id: The task ID to update.
        updates_json: JSON string with fields to update. Allowed fields:
            status (backlog|in_progress|review|done), assigned_to,
            artifact_path, title, description.
        tool_context: Strands tool context (injected by framework).

    Returns:
        Confirmation or error message.
    """
    project_id = tool_context.invocation_state.get("project_id", "")
    table_name = tool_context.invocation_state.get("board_tasks_table", "")
    phase = tool_context.invocation_state.get("phase", "")

    if not project_id or not table_name:
        return "Error: project_id or board_tasks_table not set in invocation state."

    try:
        updates: dict[str, Any] = json.loads(updates_json)
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON in updates_json: {e}"

    # Validate allowed keys and status values at the tool boundary
    allowed_keys = {"status", "assigned_to", "artifact_path", "title", "description"}
    invalid_keys = set(updates.keys()) - allowed_keys
    if invalid_keys:
        return f"Error: Invalid update fields: {invalid_keys}. Allowed: {allowed_keys}"

    valid_statuses = {"backlog", "in_progress", "review", "done"}
    if "status" in updates and updates["status"] not in valid_statuses:
        return f"Error: Invalid status '{updates['status']}'. Allowed: {valid_statuses}"

    try:
        update_task(
            table_name=table_name,
            project_id=project_id,
            phase=phase,
            task_id=task_id,
            updates=updates,
        )
        return f"Updated task {task_id}: {updates}"
    except Exception as e:
        logger.exception("Failed to update board task %s", task_id)
        return f"Error updating task: {e}"


@tool(context=True)
def add_task_comment(
    task_id: str,
    author: str,
    content: str,
    tool_context: ToolContext,
) -> str:
    """Add a comment to a board task to log progress.

    Use this to record what you did, findings, or blockers as you work.

    Args:
        task_id: The task ID to comment on.
        author: Your agent name (e.g. "pm", "sa", "dev", "infra").
        content: Comment text describing progress or findings.
        tool_context: Strands tool context (injected by framework).

    Returns:
        Confirmation or error message.
    """
    project_id = tool_context.invocation_state.get("project_id", "")
    table_name = tool_context.invocation_state.get("board_tasks_table", "")
    phase = tool_context.invocation_state.get("phase", "")

    if not project_id or not table_name:
        return "Error: project_id or board_tasks_table not set in invocation state."

    try:
        add_comment(
            table_name=table_name,
            project_id=project_id,
            phase=phase,
            task_id=task_id,
            author=author,
            content=content,
        )
        return f"Added comment to task {task_id}."
    except Exception as e:
        logger.exception("Failed to add comment to task %s", task_id)
        return f"Error adding comment: {e}"
