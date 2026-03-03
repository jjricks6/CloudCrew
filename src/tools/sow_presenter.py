"""SOW presentation tool for customer approval.

Presents the generated SOW to the customer in a dedicated review card on the
dashboard. Uses the same interrupt mechanism as ``ask_customer`` — the hook
intercepts the tool call and broadcasts a ``sow_review`` WebSocket event
with the SOW content so the dashboard can display it deterministically.

This module imports from state/ — NEVER from agents/ or hooks/.
"""

import logging

from strands import tool
from strands.types.tools import ToolContext

from src.state.interrupt_response_cache import get_and_clear_response

logger = logging.getLogger(__name__)


@tool(context=True)
def present_sow_for_approval(sow_content: str, tool_context: ToolContext) -> str:
    """Present the Statement of Work to the customer for review and approval.

    Displays the SOW to the customer in a dedicated review card on the
    dashboard. The customer can approve the SOW or request revisions.

    Call this AFTER generating the SOW with generate_sow. Pass the full
    SOW markdown text as ``sow_content`` so the dashboard can display it.
    Do NOT call ask_customer for SOW approval — use this tool instead.

    Args:
        sow_content: The full SOW markdown text to display to the customer.

    Returns:
        The customer's response: "Approved" or revision feedback text.
    """
    response = get_and_clear_response()
    if response:
        logger.info("Returning SOW approval response to agent (%d chars)", len(response))
        return response

    # Fallback — the hook should always populate the cache before the
    # tool body runs. If we get here something unexpected happened.
    logger.warning("present_sow_for_approval executed without a cached response")
    return "No response received from customer."
