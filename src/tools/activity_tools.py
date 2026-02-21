"""Activity reporting tool for the customer dashboard.

Agents call report_activity to broadcast what they're working on.
This produces the agent_active events that drive the swarm visualization.

This module imports from state/ — NEVER from agents/ or hooks/.
"""

import logging

from strands import tool
from strands.types.tools import ToolContext

from src.state.activity import store_activity_event
from src.state.broadcast import broadcast_to_project
from src.state.models import AGENT_DISPLAY_NAMES

logger = logging.getLogger(__name__)


@tool(context=True)
def report_activity(
    agent_name: str,
    detail: str,
    tool_context: ToolContext,
) -> str:
    """Report current activity to the customer dashboard.

    Call this when you start a significant task or shift focus to a new area.
    The detail text appears in the live swarm visualization so the customer
    can see what you're working on. Keep messages concise — one sentence.

    Args:
        agent_name: Your agent short name (e.g. "sa", "infra", "security").
        detail: One-sentence description of current work.
        tool_context: Strands tool context (injected by framework).

    Returns:
        Confirmation message.
    """
    project_id = tool_context.invocation_state.get("project_id", "")
    phase = tool_context.invocation_state.get("phase", "")
    activity_table = tool_context.invocation_state.get("activity_table", "")

    if not activity_table:
        return "Activity reporting not configured (no activity table)."

    if not project_id:
        return "Error: project_id not set in invocation state."

    display = AGENT_DISPLAY_NAMES.get(agent_name, agent_name)

    # Cap detail length to prevent oversized DynamoDB items and WS payloads
    max_detail = 500
    detail = detail[:max_detail]

    try:
        store_activity_event(
            table_name=activity_table,
            project_id=project_id,
            event_type="agent_active",
            agent_name=display,
            phase=phase,
            detail=detail,
        )
    except Exception:
        logger.exception(
            "report_activity | Failed to store event for agent %s",
            agent_name,
        )
        return f"Error storing activity for {agent_name}."

    try:
        broadcast_to_project(
            project_id,
            {
                "event": "agent_active",
                "project_id": project_id,
                "agent_name": display,
                "phase": phase,
                "detail": detail,
            },
        )
    except Exception:
        logger.exception(
            "report_activity | Failed to broadcast event for agent %s",
            agent_name,
        )

    logger.info(
        "Activity reported by %s (%s) in phase %s: %s",
        display,
        agent_name,
        phase,
        detail[:100],
    )
    return f"Activity reported: {detail[:80]}"
