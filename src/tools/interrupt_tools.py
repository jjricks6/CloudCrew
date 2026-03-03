"""Interrupt tools for customer communication.

Provides the ``ask_customer`` tool that lets agents pause execution and
wait for a customer response.  The actual interrupt lifecycle is managed
by ``CustomerInterruptHook`` (in src/hooks/); this tool simply reads the
cached response and returns it.

This module imports from src.state — NEVER from agents/ or hooks/.
"""

import logging

from strands import tool

from src.state.interrupt_response_cache import get_and_clear_response

logger = logging.getLogger(__name__)


@tool
def ask_customer(question: str) -> str:
    """Ask the customer a question and wait for their response.

    Use this tool when you need direct customer input during the
    engagement.  The question will be displayed on the customer dashboard
    and the customer can type their response.  You will receive their
    answer as the return value.

    Only the PM agent should call this tool.  Other agents should hand
    off to the PM with the question they need answered.

    Args:
        question: The question to ask the customer.  Be clear, concise,
            and non-technical.

    Returns:
        The customer's response text.
    """
    response = get_and_clear_response()
    if response:
        logger.info("Returning customer response to agent (%d chars)", len(response))
        return response

    # Fallback — the hook should always populate the cache before the
    # tool body runs.  If we get here something unexpected happened.
    logger.warning("ask_customer executed without a cached response")
    return "No response received from customer."
