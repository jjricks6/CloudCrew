"""Phase runner with automatic retry on failure.

Wraps Swarm invocation with configurable retry logic. On failure,
creates a fresh Swarm and re-invokes with recovery context so agents
check for existing work before starting.

This module imports from config and strands — NEVER from agents/ or tools/.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from strands.multiagent.base import Status
from strands.multiagent.swarm import Swarm, SwarmResult

from src.config import PHASE_MAX_RETRIES, PHASE_RETRY_DELAY

logger = logging.getLogger(__name__)

RECOVERY_PREFIX = (
    "IMPORTANT: This is a retry after a prior attempt failed or timed out. "
    "Work from the prior attempt may already exist in git and the task ledger. "
    "Before starting, check what already exists using git_list, git_read, "
    "and read_task_ledger. Do NOT duplicate existing work — continue from "
    "where the prior attempt left off.\n\n"
)


@dataclass
class PhaseResult:
    """Result of a phase execution, including retry metadata.

    Attributes:
        result: The SwarmResult from the final attempt.
        attempts: Total number of attempts made (1 = no retries).
        retry_history: Per-attempt metadata (attempt number, error, duration).
    """

    result: SwarmResult
    attempts: int
    retry_history: list[dict[str, Any]] = field(default_factory=list)


def run_phase(
    swarm_factory: Callable[[], Swarm],
    task: str,
    invocation_state: dict[str, Any],
    max_retries: int | None = None,
    retry_delay: float | None = None,
) -> PhaseResult:
    """Execute a phase Swarm with automatic retry on failure.

    Creates a fresh Swarm via ``swarm_factory`` for each attempt to ensure
    clean agent state. On failure (exception or Status.FAILED), prepends
    recovery context to the task and retries.

    Args:
        swarm_factory: Callable that returns a fresh Swarm instance.
            Called once per attempt to ensure clean agent state.
        task: The task prompt for the swarm.
        invocation_state: Shared invocation state dict.
        max_retries: Override for PHASE_MAX_RETRIES config. Set to 0
            to disable retry.
        retry_delay: Override for PHASE_RETRY_DELAY config (seconds).

    Returns:
        PhaseResult with the swarm result and retry metadata.

    Raises:
        Exception: Re-raises the last exception if all retry attempts
            fail with exceptions (not Status.FAILED).
    """
    retries = max_retries if max_retries is not None else PHASE_MAX_RETRIES
    delay = retry_delay if retry_delay is not None else PHASE_RETRY_DELAY
    total_attempts = retries + 1

    retry_history: list[dict[str, Any]] = []
    last_exception: Exception | None = None
    last_result: SwarmResult | None = None

    for attempt in range(1, total_attempts + 1):
        # On retry, prepend recovery context to the task
        effective_task = task if attempt == 1 else RECOVERY_PREFIX + task

        start = time.monotonic()
        try:
            swarm = swarm_factory()
            result = swarm(effective_task, invocation_state=invocation_state)
            duration = time.monotonic() - start

            retry_history.append(
                {
                    "attempt": attempt,
                    "error": None,
                    "duration_s": round(duration, 1),
                }
            )

            # Check if the swarm completed successfully
            if result.status == Status.COMPLETED:
                logger.info(
                    "Phase completed on attempt %d/%d (%.1fs)",
                    attempt,
                    total_attempts,
                    duration,
                )
                return PhaseResult(
                    result=result,
                    attempts=attempt,
                    retry_history=retry_history,
                )

            # INTERRUPTED — return immediately, do not retry.
            # The ECS entrypoint handles interrupt polling separately.
            if result.status == Status.INTERRUPTED:
                logger.info(
                    "Phase interrupted on attempt %d/%d (%.1fs)",
                    attempt,
                    total_attempts,
                    duration,
                )
                return PhaseResult(
                    result=result,
                    attempts=attempt,
                    retry_history=retry_history,
                )

            # Status is FAILED (or other non-completed) — retry if possible
            last_result = result
            last_exception = None
            logger.warning(
                "Phase attempt %d/%d returned status=%s (%.1fs)",
                attempt,
                total_attempts,
                result.status.value,
                duration,
            )

        except Exception as exc:
            duration = time.monotonic() - start
            last_exception = exc
            last_result = None

            retry_history.append(
                {
                    "attempt": attempt,
                    "error": str(exc),
                    "duration_s": round(duration, 1),
                }
            )

            logger.warning(
                "Phase attempt %d/%d failed with exception (%.1fs): %s",
                attempt,
                total_attempts,
                duration,
                exc,
            )

        # If more attempts remain, wait before retrying
        if attempt < total_attempts:
            logger.info("Retrying in %.1fs...", delay)
            time.sleep(delay)

    # All attempts exhausted
    if last_exception is not None:
        logger.error(
            "Phase failed after %d attempts. Last error: %s",
            total_attempts,
            last_exception,
        )
        raise last_exception

    # Return the last failed result (non-exception failure)
    assert last_result is not None
    logger.error(
        "Phase returned non-completed status after %d attempts: %s",
        total_attempts,
        last_result.status.value,
    )
    return PhaseResult(
        result=last_result,
        attempts=total_attempts,
        retry_history=retry_history,
    )
