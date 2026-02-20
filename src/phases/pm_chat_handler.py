"""PM Chat Lambda handler.

Invoked asynchronously by the API Lambda when a customer sends a chat
message. Creates a PM agent with a streaming callback that broadcasts
each token to the customer's dashboard via WebSocket.

This module is in phases/ — the ONLY package allowed to import from agents/.
"""

import logging
from collections.abc import Callable
from typing import Any

from src.agents.base import build_invocation_state
from src.agents.pm import create_pm_agent
from src.config import TASK_LEDGER_TABLE
from src.state.broadcast import broadcast_to_project
from src.state.chat import (
    chat_history_to_prompt,
    get_chat_history,
    new_message_id,
    store_chat_message,
)
from src.state.ledger import format_ledger, read_ledger

logger = logging.getLogger(__name__)

# Maximum number of recent messages to include as context for the PM.
CHAT_CONTEXT_LIMIT = 20


def _make_ws_callback(project_id: str, phase: str) -> Callable[..., None]:
    """Create a Strands callback_handler that broadcasts each token via WebSocket.

    Args:
        project_id: The project to broadcast to.
        phase: Current project phase (included in every event).

    Returns:
        A callback function suitable for ``Agent.callback_handler``.
    """

    def callback(*, data: str = "", complete: bool = False, **kwargs: Any) -> None:
        if data:
            broadcast_to_project(
                project_id,
                {
                    "event": "chat_chunk",
                    "project_id": project_id,
                    "phase": phase,
                    "content": data,
                },
            )

    return callback


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle an async chat invocation.

    Expected event payload::

        {
            "project_id": "...",
            "customer_message": "...",
            "message_id": "..."   # ID of the customer's message (already stored)
        }

    The handler:
    1. Loads project context (ledger + recent chat history).
    2. Broadcasts a ``chat_thinking`` event.
    3. Creates a PM agent with a streaming callback.
    4. Invokes the agent — tokens are broadcast as ``chat_chunk`` events.
    5. Broadcasts ``chat_done`` and persists the full PM response.

    Args:
        event: Async invocation payload from the API Lambda.
        context: Lambda context (unused).

    Returns:
        Dict with pm_message_id and response length.
    """
    project_id: str = event["project_id"]
    customer_message: str = event["customer_message"]

    logger.info("PM chat handler invoked for project=%s", project_id)

    # 1. Load project context
    ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
    ledger_summary = format_ledger(ledger)
    recent_messages = get_chat_history(TASK_LEDGER_TABLE, project_id, limit=CHAT_CONTEXT_LIMIT)
    conversation = chat_history_to_prompt(recent_messages)

    # 2. Broadcast thinking indicator
    broadcast_to_project(
        project_id,
        {
            "event": "chat_thinking",
            "project_id": project_id,
            "phase": ledger.current_phase.value,
        },
    )

    # 3. Create PM agent with streaming callback
    current_phase = ledger.current_phase.value
    pm = create_pm_agent()
    pm.callback_handler = _make_ws_callback(project_id, current_phase)

    invocation_state = build_invocation_state(
        project_id=project_id,
        phase=ledger.current_phase.value.lower(),
    )

    chat_task = (
        f"A customer is chatting with you about their project.\n\n"
        f"## Project Context\n{ledger_summary}\n\n"
        f"## Conversation History\n{conversation}\n\n"
        f"## Customer's Latest Message\n{customer_message}\n\n"
        f"Respond helpfully and concisely. You can use read_task_ledger and "
        f"git_read to look up specific details if needed."
    )

    # 4. Invoke — callback fires per token
    try:
        result = pm(chat_task, invocation_state=invocation_state)
        response_text = str(result)
    except Exception:
        logger.exception("PM agent failed for project=%s", project_id)
        response_text = "I'm sorry, I encountered an error while processing your message. Please try again in a moment."
        broadcast_to_project(
            project_id,
            {
                "event": "chat_chunk",
                "project_id": project_id,
                "content": response_text,
            },
        )

    # 5. Store PM response and broadcast done
    pm_message_id = new_message_id()
    store_chat_message(
        TASK_LEDGER_TABLE,
        project_id,
        pm_message_id,
        role="pm",
        content=response_text,
    )

    broadcast_to_project(
        project_id,
        {
            "event": "chat_done",
            "project_id": project_id,
            "phase": ledger.current_phase.value,
            "message_id": pm_message_id,
        },
    )

    logger.info(
        "PM chat complete for project=%s, response_length=%d",
        project_id,
        len(response_text),
    )

    return {
        "project_id": project_id,
        "pm_message_id": pm_message_id,
        "response_length": len(response_text),
    }
