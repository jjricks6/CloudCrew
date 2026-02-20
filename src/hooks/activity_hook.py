"""ActivityHook — emits agent activity events for the customer dashboard.

Captures node execution events (agent starts, completes, handoffs) and
writes them to DynamoDB for real-time WebSocket broadcast to the dashboard.

When ACTIVITY_TABLE is empty, the hook is a no-op (graceful degradation).

This module imports from strands.hooks and src.state — NEVER from agents/
or phases/.
"""

import logging
from typing import Any

from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import (
    AfterNodeCallEvent,
    BeforeNodeCallEvent,
)

from src.config import ACTIVITY_TABLE
from src.state.activity import store_activity_event
from src.state.broadcast import broadcast_to_project
from src.state.models import AGENT_DISPLAY_NAMES

logger = logging.getLogger(__name__)


def _display_name(node_id: str) -> str:
    """Translate a Strands node ID to a dashboard display name."""
    return AGENT_DISPLAY_NAMES.get(node_id, node_id)


class ActivityHook(HookProvider):
    """Hook that emits handoff and agent_idle events for the dashboard.

    Tracks which agent is active and detects handoffs between agents.
    Does NOT emit agent_active events — those come from the report_activity
    tool so agents can provide meaningful detail text.

    Events are stored in DynamoDB with 24h TTL and broadcast to connected
    WebSocket clients.

    Args:
        project_id: Project identifier for event context.
        phase: Current delivery phase name.
    """

    def __init__(self, project_id: str = "", phase: str = "") -> None:
        self._project_id = project_id
        self._phase = phase
        self._last_active_node: str = ""

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:  # noqa: ARG002
        """Register callbacks for node lifecycle events."""
        registry.add_callback(BeforeNodeCallEvent, self._on_node_start)
        registry.add_callback(AfterNodeCallEvent, self._on_node_complete)

    def _on_node_start(self, event: BeforeNodeCallEvent) -> None:
        """Detect handoffs when execution transfers between agents."""
        if not ACTIVITY_TABLE:
            return

        node_id = event.node_id
        previous_node = self._last_active_node

        # If there was a previous active node, this is a handoff
        if previous_node and previous_node != node_id:
            self._emit(
                event_type="handoff",
                agent_name=_display_name(node_id),
                detail=f"Handoff from {_display_name(previous_node)} to {_display_name(node_id)}",
            )

        self._last_active_node = node_id

    def _on_node_complete(self, event: AfterNodeCallEvent) -> None:
        """Emit agent_idle event when a node finishes execution."""
        if not ACTIVITY_TABLE:
            return

        node_id = event.node_id
        display = _display_name(node_id)
        swarm = event.source
        state = getattr(swarm, "state", None)
        results = getattr(state, "results", {}) if state else {}
        node_result = results.get(node_id)

        detail = f"{display} finished"
        if node_result is not None and isinstance(node_result.result, Exception):
            detail = f"{display} encountered an error: {node_result.result}"

        self._emit(
            event_type="agent_idle",
            agent_name=display,
            detail=detail,
        )

    def _emit(self, event_type: str, agent_name: str, detail: str) -> None:
        """Write an activity event to DynamoDB and broadcast via WebSocket.

        Failures are logged but never raised — activity tracking must not
        crash the agent swarm.
        """
        try:
            store_activity_event(
                table_name=ACTIVITY_TABLE,
                project_id=self._project_id,
                event_type=event_type,
                agent_name=agent_name,
                phase=self._phase,
                detail=detail,
            )
        except Exception:
            logger.exception(
                "activity_hook | Failed to store event %s for agent %s",
                event_type,
                agent_name,
            )

        try:
            broadcast_to_project(
                self._project_id,
                {
                    "event": event_type,
                    "project_id": self._project_id,
                    "agent_name": agent_name,
                    "phase": self._phase,
                    "detail": detail,
                },
            )
        except Exception:
            logger.exception(
                "activity_hook | Failed to broadcast event %s for agent %s",
                event_type,
                agent_name,
            )
