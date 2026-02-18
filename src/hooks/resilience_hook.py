"""Resilience observability hook for structured failure tracking.

Logs structured data about node execution outcomes and swarm completion.
This module imports from strands.hooks only — NEVER from agents/, tools/,
or phases/.
"""

import logging
from typing import Any

from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import (
    AfterMultiAgentInvocationEvent,
    AfterNodeCallEvent,
    BeforeNodeCallEvent,
)

logger = logging.getLogger(__name__)


class ResilienceHook(HookProvider):
    """Hook that logs structured resilience/observability data.

    Tracks node execution outcomes (success, failure, timeout) and
    swarm-level completion status for operational monitoring.
    """

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:  # noqa: ARG002
        """Register callbacks for node and swarm lifecycle events."""
        registry.add_callback(BeforeNodeCallEvent, self._on_node_start)
        registry.add_callback(AfterNodeCallEvent, self._on_node_complete)
        registry.add_callback(
            AfterMultiAgentInvocationEvent,
            self._on_swarm_complete,
        )

    def _on_node_start(self, event: BeforeNodeCallEvent) -> None:
        """Log when a node begins execution."""
        swarm_id = getattr(event.source, "id", "unknown")
        logger.info(
            "node_start | swarm=%s node=%s",
            swarm_id,
            event.node_id,
        )

    def _on_node_complete(self, event: AfterNodeCallEvent) -> None:
        """Log node completion with status and timing."""
        swarm = event.source
        swarm_id = getattr(swarm, "id", "unknown")

        # Access NodeResult from swarm state
        state = getattr(swarm, "state", None)
        results = getattr(state, "results", {}) if state else {}
        node_result = results.get(event.node_id)

        status = "unknown"
        exec_time_ms = 0
        error_msg = ""

        if node_result is not None:
            status = node_result.status.value if hasattr(node_result.status, "value") else str(node_result.status)
            exec_time_ms = getattr(node_result, "execution_time", 0)
            if isinstance(node_result.result, Exception):
                error_msg = str(node_result.result)

        if error_msg:
            logger.warning(
                "node_complete | swarm=%s node=%s status=%s time_ms=%d error=%s",
                swarm_id,
                event.node_id,
                status,
                exec_time_ms,
                error_msg,
            )
        else:
            logger.info(
                "node_complete | swarm=%s node=%s status=%s time_ms=%d",
                swarm_id,
                event.node_id,
                status,
                exec_time_ms,
            )

    def _on_swarm_complete(self, event: AfterMultiAgentInvocationEvent) -> None:
        """Log swarm completion with overall status."""
        swarm = event.source
        swarm_id = getattr(swarm, "id", "unknown")
        state = getattr(swarm, "state", None)

        status = "unknown"
        node_count = 0
        exec_time_ms = 0

        if state is not None:
            completion_status: Any = getattr(state, "completion_status", None)
            status = completion_status.value if hasattr(completion_status, "value") else str(completion_status)
            node_history = getattr(state, "node_history", [])
            node_count = len(node_history)
            exec_time_ms = getattr(state, "execution_time", 0)

        logger.info(
            "swarm_complete | swarm=%s status=%s nodes=%d time_ms=%d",
            swarm_id,
            status,
            node_count,
            exec_time_ms,
        )
