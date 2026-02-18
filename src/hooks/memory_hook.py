"""Memory hook for loading LTM context and saving STM conversations.

This hook integrates AgentCore Memory into the agent invocation lifecycle.
It imports from strands.hooks and src.state — NEVER from agents/ or tools/.
"""

import logging
from typing import Any

from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import AfterInvocationEvent, BeforeInvocationEvent

from src.state.memory import MemoryClient

logger = logging.getLogger(__name__)


class MemoryHook(HookProvider):
    """Hook that loads LTM context before invocation and saves to STM after.

    Attach to agents or swarms to enable cross-phase memory:
    - Before invocation: retrieves relevant LTM records and injects context
    - After invocation: saves the conversation to STM for future reference

    Args:
        stm_memory_id: AgentCore Memory ID for short-term memory. Empty to disable.
        ltm_memory_id: AgentCore Memory ID for long-term memory. Empty to disable.
    """

    def __init__(self, stm_memory_id: str = "", ltm_memory_id: str = "") -> None:
        self._stm: MemoryClient | None = MemoryClient(stm_memory_id) if stm_memory_id else None
        self._ltm: MemoryClient | None = MemoryClient(ltm_memory_id) if ltm_memory_id else None

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:  # noqa: ARG002
        """Register memory lifecycle callbacks.

        Args:
            registry: The hook registry to register with.
            **kwargs: Additional keyword arguments (required by HookProvider protocol).
        """
        registry.add_callback(BeforeInvocationEvent, self.load_context)
        registry.add_callback(AfterInvocationEvent, self.save_context)

    def load_context(self, event: BeforeInvocationEvent) -> None:
        """Load relevant LTM context before agent invocation.

        Retrieves decisions and project context from LTM and prepends
        them to the agent's message history so the agent has cross-phase
        awareness.

        Args:
            event: The before-invocation event with agent and state info.
        """
        if not self._ltm:
            return

        project_id = event.invocation_state.get("project_id", "")
        if not project_id:
            return

        try:
            records = self._ltm.retrieve(
                query=f"project {project_id} decisions and context",
                namespace="/decisions/",
                max_results=5,
            )
            if records and event.messages is not None:
                context_parts: list[str] = []
                for record in records:
                    text = _extract_record_text(record)
                    if text:
                        context_parts.append(text)

                if context_parts:
                    context_text = "## Context from Previous Phases\n\n" + "\n\n".join(context_parts)
                    # Prepend as a system-like user message
                    event.messages.insert(
                        0,
                        {"role": "user", "content": [{"text": context_text}]},
                    )
                    logger.info(
                        "Loaded %d LTM records for project %s",
                        len(context_parts),
                        project_id,
                    )
        except Exception:
            logger.exception("Failed to load LTM context for project %s", project_id)

    def save_context(self, event: AfterInvocationEvent) -> None:
        """Save conversation to STM after agent invocation.

        Extracts the agent's final response and saves it as an STM event
        for potential future LTM extraction.

        Args:
            event: The after-invocation event with agent result.
        """
        if not self._stm:
            return

        session_id = event.invocation_state.get("session_id", "")
        if not session_id:
            return

        try:
            events: list[dict[str, str]] = []
            if event.result and event.result.message:
                message = event.result.message
                content_blocks = message.get("content", [])
                for block in content_blocks:
                    if isinstance(block, dict) and "text" in block:
                        events.append({"content": block["text"]})

            if events:
                agent_name = getattr(event.agent, "name", "unknown")
                self._stm.save_events(
                    session_id=session_id,
                    events=events,
                    namespace=f"/sessions/{session_id}/{agent_name}/",
                )
                logger.info(
                    "Saved %d events to STM for session %s",
                    len(events),
                    session_id,
                )
        except Exception:
            logger.exception("Failed to save STM context for session %s", session_id)


def _extract_record_text(record: dict[str, Any]) -> str:
    """Extract text content from a memory record.

    Args:
        record: A memory record dict from AgentCore Memory.

    Returns:
        The text content, or empty string if not found.
    """
    content = record.get("content", {})
    if isinstance(content, dict):
        text: str = content.get("text", "")
        return text
    if isinstance(content, str):
        return content
    return ""
