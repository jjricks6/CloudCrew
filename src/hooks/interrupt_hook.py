"""CustomerInterruptHook — enables agents to ask the customer questions.

Intercepts the ``ask_customer`` and ``present_sow_for_approval`` tool calls
via ``BeforeToolCallEvent`` and uses the Strands SDK's native interrupt
mechanism to pause the Swarm until the customer responds.

Flow (ask_customer):
    1. Agent calls ``ask_customer(question="...")``.
    2. This hook fires **before** the tool executes.
    3. First invocation: ``event.interrupt()`` raises ``InterruptException``
       → Swarm enters ``INTERRUPTED`` status → ECS runner stores the question
       in DynamoDB and polls for a customer response.
    4. Customer responds via the dashboard.
    5. ECS runner resumes the Swarm with ``interruptResponse`` blocks.
    6. Second invocation: ``event.interrupt()`` **returns** the response.
    7. Hook caches the response via ``interrupt_response_cache``.
    8. The ``ask_customer`` tool executes, reads the cache, and returns the
       response to the agent.

Flow (present_sow_for_approval):
    Same interrupt mechanism, but the ECS runner's ``store_interrupt`` call
    includes a ``sow_review:`` prefix in the question field. The state module
    detects this prefix and broadcasts a ``sow_review`` WebSocket event
    (with SOW content) instead of the generic ``interrupt_raised`` event.

This module imports from strands.hooks and src.state — NEVER from agents/
or tools/.
"""

import logging
from typing import Any

from strands.hooks import BeforeToolCallEvent, HookProvider, HookRegistry

from src.state.interrupt_response_cache import set_response

logger = logging.getLogger(__name__)

# Tool names that trigger the interrupt mechanism
_INTERRUPT_TOOLS = {"ask_customer", "present_sow_for_approval"}

# Prefix added to the interrupt reason for SOW review events so the
# state module can distinguish them from regular questions.
SOW_REVIEW_PREFIX = "sow_review:"


class CustomerInterruptHook(HookProvider):
    """Hook that intercepts customer-facing tool calls and raises SDK interrupts.

    Register this hook on the PM agent (or any agent that needs to ask
    the customer questions). The hook works in tandem with the
    ``ask_customer`` and ``present_sow_for_approval`` tools.
    """

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:  # noqa: ARG002
        """Register the BeforeToolCallEvent callback."""
        registry.add_callback(BeforeToolCallEvent, self._on_before_tool_call)

    def _on_before_tool_call(self, event: BeforeToolCallEvent) -> None:
        """Intercept customer-facing tools and raise an interrupt.

        On the first invocation, ``event.interrupt()`` raises
        ``InterruptException`` which pauses the agent. On the second
        invocation (after resume), it returns the customer's response.
        """
        tool_name = event.tool_use["name"]
        if tool_name not in _INTERRUPT_TOOLS:
            return

        if tool_name == "present_sow_for_approval":
            sow_text = event.tool_use.get("input", {}).get("sow_content", "")
            reason = f"{SOW_REVIEW_PREFIX}{sow_text}"
            logger.info(
                "present_sow_for_approval intercepted — raising SOW review interrupt (%d chars)",
                len(sow_text),
            )
        else:
            reason = event.tool_use.get("input", {}).get("question", "")
            logger.info("ask_customer intercepted | question=%s", reason[:120])

        # First call: raises InterruptException (stops agent loop).
        # Second call (after resume): returns the customer's response.
        response = event.interrupt(tool_name, reason=reason)

        # If we reach here, the customer has responded.
        logger.info("Customer responded to interrupt (%d chars)", len(str(response)))
        set_response(str(response))
