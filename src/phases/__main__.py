"""ECS phase runner entrypoint.

Invoked by ECS Fargate tasks launched from Step Functions via Lambda.
Reads environment variables to determine which phase to execute, runs
the appropriate Swarm, handles interrupts (HITL), and reports results
back to Step Functions.

Entry point: ``python -m src.phases``

This module is in phases/ — the ONLY package allowed to import from agents/.
"""

import json
import logging
import os
import sys
import time
import uuid
from collections.abc import Callable
from typing import Any

import boto3

from src.config import (
    AWS_REGION,
    INTERRUPT_POLL_INTERVAL,
    INTERRUPT_POLL_TIMEOUT,
    PHASE_MAX_RETRIES,
    PHASE_RETRY_DELAY,
    TASK_LEDGER_TABLE,
)
from src.phases.runner import RECOVERY_PREFIX
from src.state.interrupts import get_interrupt_response, store_interrupt

logger = logging.getLogger(__name__)

# Phase name -> swarm factory import path.
# Lazy imports to avoid loading all agents at module level.
_PHASE_FACTORIES: dict[str, str] = {
    "DISCOVERY": "src.phases.discovery:create_discovery_swarm",
    "ARCHITECTURE": "src.phases.architecture:create_architecture_swarm",
    "POC": "src.phases.poc:create_poc_swarm",
    "PRODUCTION": "src.phases.production:create_production_swarm",
    "HANDOFF": "src.phases.handoff:create_handoff_swarm",
}


def get_swarm_factory(phase: str) -> Callable[..., Any]:
    """Resolve a phase name to its swarm factory callable.

    Args:
        phase: The phase name (e.g., "DISCOVERY", "ARCHITECTURE").

    Returns:
        The swarm factory callable.

    Raises:
        ValueError: If the phase is not recognized.
    """
    import importlib

    factory_path = _PHASE_FACTORIES.get(phase.upper())
    if not factory_path:
        valid = ", ".join(sorted(_PHASE_FACTORIES.keys()))
        msg = f"Unknown phase '{phase}'. Valid phases: {valid}"
        raise ValueError(msg)

    module_path, func_name = factory_path.rsplit(":", 1)
    module = importlib.import_module(module_path)
    return getattr(module, func_name)  # type: ignore[no-any-return]  # Dynamic import returns Any


def _build_invocation_state(project_id: str, phase: str) -> dict[str, Any]:
    """Build invocation state from the base module."""
    from src.agents.base import build_invocation_state

    return build_invocation_state(project_id=project_id, phase=phase.lower())


def _send_task_success(task_token: str, output: dict[str, Any]) -> None:
    """Report success to Step Functions."""
    client = boto3.client("stepfunctions", region_name=AWS_REGION)
    client.send_task_success(
        taskToken=task_token,
        output=json.dumps(output),
    )
    logger.info("Sent task success to Step Functions")


def _send_task_failure(task_token: str, error: str, cause: str) -> None:
    """Report failure to Step Functions."""
    client = boto3.client("stepfunctions", region_name=AWS_REGION)
    client.send_task_failure(
        taskToken=task_token,
        error=error,
        cause=cause[:256],
    )
    logger.info("Sent task failure to Step Functions: %s", error)


def _poll_for_interrupt_responses(
    project_id: str,
    interrupt_ids: list[str],
) -> dict[str, str]:
    """Poll DynamoDB until all interrupt responses are received.

    Args:
        project_id: The project identifier.
        interrupt_ids: List of interrupt IDs to poll.

    Returns:
        Mapping of interrupt_id -> response text.

    Raises:
        TimeoutError: If polling exceeds INTERRUPT_POLL_TIMEOUT.
    """
    responses: dict[str, str] = {}
    pending = set(interrupt_ids)
    start = time.monotonic()

    while pending:
        elapsed = time.monotonic() - start
        if elapsed > INTERRUPT_POLL_TIMEOUT:
            msg = f"Interrupt polling timed out after {elapsed:.0f}s. Pending: {pending}"
            raise TimeoutError(msg)

        for iid in list(pending):
            resp = get_interrupt_response(TASK_LEDGER_TABLE, project_id, iid)
            if resp:
                responses[iid] = resp
                pending.discard(iid)
                logger.info("Received response for interrupt %s", iid)

        if pending:
            time.sleep(INTERRUPT_POLL_INTERVAL)

    return responses


def execute_phase(
    project_id: str,
    phase: str,
    task_token: str,
    customer_feedback: str = "",
) -> None:
    """Execute a phase with interrupt handling and retry logic.

    This is the main execution function for the ECS entrypoint.

    The flow:
    1. Create Swarm via factory
    2. Invoke Swarm
    3. If INTERRUPTED -> store interrupts, poll for responses, resume Swarm
    4. If COMPLETED -> report success to Step Functions
    5. If FAILED -> retry with fresh Swarm (up to PHASE_MAX_RETRIES)

    Args:
        project_id: The project identifier.
        phase: The phase to execute.
        task_token: Step Functions task token for reporting results.
        customer_feedback: Optional feedback from a prior revision request.
    """
    factory = get_swarm_factory(phase)
    invocation_state = _build_invocation_state(project_id, phase)

    task = f"Execute the {phase} phase for project {project_id}."
    if customer_feedback:
        task += (
            f"\n\nThe customer provided feedback on the previous submission:\n"
            f"{customer_feedback}\n\n"
            f"Address this feedback in your work."
        )

    last_error = ""

    for attempt in range(1, PHASE_MAX_RETRIES + 2):
        effective_task = task if attempt == 1 else RECOVERY_PREFIX + task

        try:
            swarm = factory(project_id=project_id, phase=phase)
            result = swarm(effective_task, invocation_state=invocation_state)

            # Handle interrupt loop (same Swarm instance)
            from strands.multiagent.base import Status

            while result.status == Status.INTERRUPTED:
                interrupts = _extract_interrupts(result)
                if not interrupts:
                    logger.warning("INTERRUPTED status but no interrupt data found")
                    break

                # Store interrupts in DynamoDB
                interrupt_ids = []
                for q in interrupts:
                    iid = str(uuid.uuid4())
                    store_interrupt(TASK_LEDGER_TABLE, project_id, iid, q, phase=phase)
                    interrupt_ids.append(iid)

                # Poll for customer responses
                responses = _poll_for_interrupt_responses(project_id, interrupt_ids)

                # Resume the swarm with responses
                combined_response = "\n\n".join(
                    f"Q: {interrupts[i]}\nA: {responses[interrupt_ids[i]]}" for i in range(len(interrupts))
                )
                result = swarm(
                    f"Customer responded to your questions:\n\n{combined_response}\n\nPlease continue.",
                    invocation_state=invocation_state,
                )

            if result.status == Status.COMPLETED:
                # Generate phase summary before reporting success
                logger.info("Phase completed. Generating phase summary...")
                try:
                    _invoke_pm_for_phase_summary(
                        project_id=project_id,
                        phase=phase,
                        invocation_state=invocation_state,
                    )
                except Exception as exc:
                    logger.exception("Failed to generate phase summary: %s", exc)
                    # Continue regardless — summary generation is non-critical

                _send_task_success(
                    task_token,
                    {
                        "project_id": project_id,
                        "phase": phase,
                        "status": "COMPLETED",
                        "attempts": attempt,
                    },
                )
                return

            # Non-completed, non-interrupted status — retry
            last_error = f"Phase returned status: {result.status.value}"
            logger.warning("Attempt %d: %s", attempt, last_error)

        except TimeoutError:
            last_error = "Interrupt polling timed out"
            logger.exception("Attempt %d: %s", attempt, last_error)
            break  # Don't retry timeout — customer isn't responding
        except Exception as exc:
            last_error = str(exc)
            logger.exception("Attempt %d failed: %s", attempt, last_error)

        if attempt <= PHASE_MAX_RETRIES:
            logger.info("Retrying in %.1fs...", PHASE_RETRY_DELAY)
            time.sleep(PHASE_RETRY_DELAY)

    _send_task_failure(task_token, "PhaseExecutionFailed", last_error)


def _invoke_pm_for_phase_summary(
    project_id: str,
    phase: str,
    invocation_state: dict[str, Any],
) -> None:
    """Invoke PM agent to generate phase summary after phase completes.

    This is a standalone invocation of the PM agent in a single-node Swarm.
    The PM reads the task ledger and git artifacts to synthesize a summary,
    then writes it to docs/phase-summaries/{phase-name}.md.

    Args:
        project_id: The project identifier.
        phase: The phase name that just completed.
        invocation_state: The invocation state with memory context.
    """
    from strands.multiagent.swarm import Swarm

    from src.agents.pm import create_pm_agent
    from src.phases.runner import run_phase

    # Build task for PM
    task = f"""Phase {phase} has completed. Review what was accomplished and generate a comprehensive Phase Summary.

Instructions:
1. Read the task ledger for this project to understand decisions and deliverables
2. Review git artifacts in docs/, security/, infra/, app/, and data/ directories
3. Synthesize into an executive-friendly Phase Summary document
4. Save to docs/phase-summaries/{phase.lower()}.md using git_write_phase_summary

The summary should:
- Lead with value delivered to the customer
- Highlight key technical decisions and trade-offs made
- List all deliverables with their status
- Note any risks or follow-up items
- Be suitable for customer review (professional, non-technical language)

Ensure the summary file is committed to git before completing."""

    # Create factory that produces a single-node Swarm with just PM
    def create_pm_only_swarm() -> Swarm:
        """Create a Swarm with only the PM agent."""
        pm_agent = create_pm_agent()
        return Swarm(
            nodes=[pm_agent],
            entry_point=pm_agent,
            max_handoffs=0,  # PM doesn't need to handoff
            max_iterations=1,
            id="pm-phase-summary-swarm",
        )

    try:
        result = run_phase(
            swarm_factory=create_pm_only_swarm,
            task=task,
            invocation_state=invocation_state,
            max_retries=1,
        )
        logger.info(
            "Phase summary generation completed with status: %s",
            result.result.status if result.result else "None",
        )
    except Exception as exc:
        logger.exception("Phase summary generation failed: %s", exc)
        # Re-raise to be caught by caller's exception handler
        raise


def _extract_interrupts(result: Any) -> list[str]:
    """Extract interrupt questions from a SwarmResult.

    Args:
        result: The SwarmResult with INTERRUPTED status.

    Returns:
        List of question strings from the interrupt data.
    """
    interrupts: list[str] = []
    # Access interrupt data from the swarm result
    interrupt_data = getattr(result, "interrupts", None)
    if interrupt_data and isinstance(interrupt_data, list):
        for item in interrupt_data:
            question = getattr(item, "query", None) or str(item)
            interrupts.append(question)
    return interrupts


def main() -> None:
    """Main entry point for the ECS phase runner."""
    # Strands SDK uses recursive event_loop_cycle — each tool call adds ~7 stack
    # frames.  Agents that make 40+ sequential tool calls (e.g. Infra doing
    # validate/fix cycles) can exceed Python's default 1000-frame limit.
    sys.setrecursionlimit(50000)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    project_id = os.environ.get("PROJECT_ID", "")
    phase = os.environ.get("PHASE", "")
    task_token = os.environ.get("TASK_TOKEN", "")
    customer_feedback = os.environ.get("CUSTOMER_FEEDBACK", "")

    if not project_id or not phase or not task_token:
        logger.error(
            "Missing required env vars: PROJECT_ID=%s, PHASE=%s, TASK_TOKEN=%s",
            bool(project_id),
            bool(phase),
            bool(task_token),
        )
        sys.exit(1)

    logger.info("Starting phase runner: project=%s, phase=%s", project_id, phase)

    try:
        execute_phase(project_id, phase, task_token, customer_feedback)
    except Exception:
        logger.exception("Fatal error in phase runner")
        try:
            _send_task_failure(task_token, "FatalError", "Unhandled exception in phase runner")
        except Exception:
            logger.exception("Failed to report failure to Step Functions")
        sys.exit(1)


if __name__ == "__main__":
    main()
