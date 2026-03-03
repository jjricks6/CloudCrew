"""In-process cache for interrupt responses.

Bridges the CustomerInterruptHook (which receives responses from the Strands
SDK interrupt mechanism) and the ask_customer tool (which returns the
response to the calling agent).

This module is imported by both hooks/ and tools/ — it lives in state/
to respect module boundary rules.

This module imports from config — NEVER from agents/, tools/, or phases/.
"""

import logging
import threading

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_response: str = ""


def set_response(response: str) -> None:
    """Store a customer's interrupt response for the ask_customer tool to read.

    Args:
        response: The customer's response text.
    """
    global _response
    with _lock:
        _response = response
    logger.debug("Cached interrupt response (%d chars)", len(response))


def get_and_clear_response() -> str:
    """Get and clear the stored interrupt response.

    Returns:
        The customer's response text, or empty string if none is cached.
    """
    global _response
    with _lock:
        result = _response
        _response = ""
    return result
