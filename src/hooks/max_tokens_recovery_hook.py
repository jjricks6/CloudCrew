"""MaxTokensRecoveryHook — graceful recovery from output token limit.

When an agent's response exceeds the model's max_tokens limit, this hook
intercepts the failure and retries the model call with guidance to produce
shorter output.  Without this hook, MaxTokensReachedException crashes the
entire agent loop.

This module imports from strands.hooks only — NEVER from agents/, tools/,
or phases/.
"""

import logging
from typing import Any

from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import AfterModelCallEvent

logger = logging.getLogger(__name__)

# Max consecutive retries per agent before giving up
MAX_RETRIES = 2

_RETRY_GUIDANCE = (
    "Your previous response was truncated because it exceeded the output token limit. "
    "Please try again with SHORTER output. Strategies:\n"
    "- Write ONE file at a time instead of using batch writes\n"
    "- Keep each file under 150 lines\n"
    "- If you need to write multiple files, do them in separate tool calls "
    "across multiple responses\n"
    "- Summarize rather than reproduce large content"
)


class MaxTokensRecoveryHook(HookProvider):
    """Hook that catches max_tokens stop reason and retries with guidance.

    Instead of crashing with MaxTokensReachedException, this hook:
    1. Detects when a model response was truncated (stop_reason == "max_tokens")
    2. Injects a message telling the model to produce shorter output
    3. Sets retry=True so the agent loop re-invokes the model
    4. After MAX_RETRIES consecutive failures, allows the exception to propagate

    The retry counter is tracked per agent name so one agent's retries
    don't affect another agent in the same Swarm.
    """

    def __init__(self) -> None:
        self._retries: dict[str, int] = {}

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:  # noqa: ARG002
        """Register callback for AfterModelCallEvent."""
        registry.add_callback(AfterModelCallEvent, self._on_after_model_call)

    def _on_after_model_call(self, event: AfterModelCallEvent) -> None:
        """Handle model call completion — recover from max_tokens if possible."""
        if event.stop_response is None:
            return

        agent_name = getattr(event.agent, "name", "unknown")

        if event.stop_response.stop_reason != "max_tokens":
            # Successful completion — reset retry counter for this agent
            if agent_name in self._retries:
                del self._retries[agent_name]
            return

        retries = self._retries.get(agent_name, 0) + 1
        self._retries[agent_name] = retries

        if retries > MAX_RETRIES:
            logger.error(
                "max_tokens_recovery | agent=%s exhausted %d retries, "
                "allowing MaxTokensReachedException to propagate",
                agent_name,
                MAX_RETRIES,
            )
            return

        logger.warning(
            "max_tokens_recovery | agent=%s retry %d/%d — " "injecting guidance and retrying model call",
            agent_name,
            retries,
            MAX_RETRIES,
        )

        # Inject guidance into the agent's message history so the model
        # knows its previous attempt was truncated and should be shorter.
        messages = event.agent.messages
        messages.append(
            {
                "role": "assistant",
                "content": [
                    {"text": "[Response truncated — exceeded output token limit]"},
                ],
            },
        )
        messages.append(
            {
                "role": "user",
                "content": [{"text": _RETRY_GUIDANCE}],
            },
        )

        event.retry = True
