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
from collections.abc import Callable
from typing import Any

import boto3

from src.config import (
    AWS_REGION,
    ECS_CUSTOMER_FEEDBACK,
    ECS_PHASE,
    ECS_PROJECT_ID,
    ECS_TASK_TOKEN,
    INTERRUPT_POLL_INTERVAL,
    INTERRUPT_POLL_TIMEOUT,
    PHASE_MAX_RETRIES,
    PHASE_RETRY_DELAY,
    PROJECT_REPO_PATH,
    TASK_LEDGER_TABLE,
)
from src.phases.git_ops import push_to_remote, setup_git_repo, sync_artifacts_to_s3
from src.phases.runner import RECOVERY_PREFIX
from src.state.interrupts import SOW_REVIEW_PREFIX, get_interrupt_response, store_interrupt

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
    """Poll DynamoDB until all interrupt responses are received."""
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


def _discovery_sow_validated(project_id: str) -> bool:
    """Return True if the task ledger has facts (SOW was parsed after approval)."""
    from src.state.ledger import read_ledger

    ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
    if ledger.facts:
        logger.info(
            "Discovery SOW validated: %d facts in ledger for project=%s",
            len(ledger.facts),
            project_id,
        )
        return True

    logger.warning(
        "Discovery SOW NOT validated: no facts in ledger for project=%s",
        project_id,
    )
    return False


def execute_phase(
    project_id: str,
    phase: str,
    task_token: str,
    customer_feedback: str = "",
) -> None:
    """Execute a phase: run Swarm, handle interrupts, report to Step Functions."""
    # Set up the git repo — clone customer's repo if credentials exist,
    # otherwise fall back to a temporary local repo.
    if not PROJECT_REPO_PATH:
        repo_dir = setup_git_repo(project_id)
        os.environ["PROJECT_REPO_PATH"] = str(repo_dir)

    factory = get_swarm_factory(phase)
    invocation_state = _build_invocation_state(project_id, phase)

    # For Discovery phase, check if SOW needs to be generated
    task = f"Execute the {phase} phase for project {project_id}."
    if phase == "DISCOVERY":
        from src.state.ledger import read_ledger

        ledger = read_ledger(TASK_LEDGER_TABLE, project_id)

        if ledger.initial_requirements and not ledger.facts:
            # SOW not generated yet - instruct PM to ask questions then generate
            project_name = ledger.project_name or project_id
            task = f"""Project Name: {project_name}

The customer already provided the following initial requirements at project creation:

{ledger.initial_requirements}

IMPORTANT: The project name and initial requirements above are already known.
Do NOT ask the customer to repeat their project name or restate what they
already told you. Start by acknowledging what they've shared, then ask
clarifying questions about details they did NOT already cover.

Your task for Discovery phase:

1. Ask the customer clarifying questions ONE AT A TIME to fill in gaps.
   Do NOT ask multiple questions at once. Ask ONE question, receive the answer,
   then decide if you need to ask another question or if you have enough information.

2. Once you have sufficient information, generate a comprehensive Statement of Work (SOW).

3. Save the SOW to docs/project-plan/sow.md using git_write_project_plan.

4. Show the SOW to the customer and ask for approval. If they request changes,
   incorporate their feedback and regenerate. Repeat until approved.

5. After SOW is approved, parse it using parse_sow to extract structured requirements.

6. Record all requirements, objectives, and constraints in the task ledger.

7. Create initial board tasks for the project.

IMPORTANT: Ask questions ONE AT A TIME. This creates a natural, conversational
experience where the customer can thoughtfully answer each question before
you ask the next one."""

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
                interrupt_objects = getattr(result, "interrupts", None) or []
                if not interrupt_objects:
                    logger.warning("INTERRUPTED status but no interrupt data found")
                    break

                # Store interrupts in DynamoDB using the SDK's interrupt IDs
                for interrupt_obj in interrupt_objects:
                    question = str(getattr(interrupt_obj, "reason", None) or interrupt_obj)

                    # For SOW review interrupts, the SOW content is appended
                    # to the reason string after the "sow_review:" prefix by
                    # the interrupt hook.  Extract it so store_interrupt can
                    # broadcast it to the dashboard via WebSocket.
                    sow_content = ""
                    if question.startswith(SOW_REVIEW_PREFIX):
                        sow_content = question[len(SOW_REVIEW_PREFIX) :]
                        if sow_content:
                            logger.info("Extracted SOW content from interrupt reason (%d chars)", len(sow_content))
                        else:
                            logger.warning("SOW review interrupt has no content attached")

                    store_interrupt(
                        TASK_LEDGER_TABLE,
                        project_id,
                        interrupt_obj.id,
                        question,
                        phase=phase,
                        sow_content=sow_content,
                    )

                # Poll for customer responses
                interrupt_ids = [obj.id for obj in interrupt_objects]
                responses = _poll_for_interrupt_responses(project_id, interrupt_ids)

                # Resume the swarm with interruptResponse blocks (SDK-native format)
                interrupt_responses: list[dict[str, Any]] = [
                    {
                        "interruptResponse": {
                            "interruptId": obj.id,
                            "response": responses[obj.id],
                        },
                    }
                    for obj in interrupt_objects
                ]
                result = swarm(interrupt_responses, invocation_state=invocation_state)

            if result.status == Status.COMPLETED:
                # Discovery gate: validate the SOW was presented for customer
                # approval and parsed before allowing the phase to complete.
                # The PM sometimes completes after writing the SOW to git
                # without presenting it for approval — catch that here and
                # re-invoke the Swarm with recovery instructions.
                if phase == "DISCOVERY" and not _discovery_sow_validated(project_id):
                    logger.warning(
                        "Discovery completed without SOW approval/parsing. Re-invoking swarm to complete SOW flow."
                    )
                    recovery_task = (
                        "IMPORTANT: Discovery completed prematurely. The SOW was "
                        "saved to git but NOT presented for customer approval.\n\n"
                        "1. Read the SOW from docs/project-plan/sow.md using git_read\n"
                        "2. Present it using present_sow_for_approval (full SOW text)\n"
                        "3. If changes requested, incorporate and regenerate\n"
                        "4. After approval, parse with parse_sow\n"
                        "5. Record requirements in task ledger via update_task_ledger\n"
                        "6. Create initial board tasks\n\n"
                        "Do NOT complete until ALL steps are done."
                    )
                    # Create a fresh swarm and run the recovery task
                    swarm = factory(project_id=project_id, phase=phase)
                    result = swarm(recovery_task, invocation_state=invocation_state)
                    # Re-enter the interrupt handling loop for SOW approval
                    continue

                # Generate phase summary before reporting success (with retry)
                logger.info("Phase completed. Generating phase summary...")
                _generate_phase_summary_with_retry(
                    project_id=project_id,
                    phase=phase,
                    invocation_state=invocation_state,
                )

                # Sync repo artifacts to S3 so the API Lambda can serve them
                repo_path = os.environ.get("PROJECT_REPO_PATH", "")
                if repo_path:
                    sync_artifacts_to_s3(project_id, repo_path, phase)
                    push_to_remote(project_id, repo_path, phase)

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


def _generate_phase_summary_with_retry(
    project_id: str,
    phase: str,
    invocation_state: dict[str, Any],
    max_retries: int = 3,
) -> None:
    """Generate phase summary via PM agent with retry. Non-blocking on failure."""
    from strands.multiagent.swarm import Swarm

    from src.agents.pm import create_pm_agent
    from src.hooks.max_tokens_recovery_hook import MaxTokensRecoveryHook
    from src.hooks.resilience_hook import ResilienceHook
    from src.phases.runner import run_phase

    task = (
        f"Phase {phase} has completed. Generate a Phase Summary.\n\n"
        f"1. Read the task ledger for decisions and deliverables\n"
        f"2. Review git artifacts in docs/, security/, infra/, app/, data/\n"
        f"3. Synthesize into an executive-friendly summary\n"
        f"4. Save to docs/phase-summaries/{phase.lower()}.md via git_write_phase_summary\n\n"
        f"Focus on value delivered, key decisions, deliverables, and risks."
    )

    def create_pm_only_swarm() -> Swarm:
        pm_agent = create_pm_agent()
        return Swarm(
            nodes=[pm_agent],
            entry_point=pm_agent,
            max_handoffs=0,
            max_iterations=5,
            hooks=[ResilienceHook(), MaxTokensRecoveryHook()],
            id="pm-phase-summary-swarm",
        )

    for attempt in range(1, max_retries + 1):
        try:
            result = run_phase(
                swarm_factory=create_pm_only_swarm,
                task=task,
                invocation_state=invocation_state,
                max_retries=1,
            )
            status = result.result.status if result.result else None
            if status and status.value == "completed":
                logger.info("Phase summary generated for phase %s", phase)
                return
            # Swarm returned but with non-completed status — treat as failure
            logger.warning(
                "Phase summary attempt %d/%d returned status=%s for project=%s, phase=%s",
                attempt,
                max_retries,
                status,
                project_id,
                phase,
            )
        except Exception as exc:
            logger.warning(
                "Phase summary generation failed (attempt %d/%d) for project=%s, phase=%s: %s",
                attempt,
                max_retries,
                project_id,
                phase,
                type(exc).__name__,
            )
        if attempt < max_retries:
            time.sleep(2.0)
        else:
            logger.error(
                "Phase summary generation failed after %d attempts for project=%s, phase=%s",
                max_retries,
                project_id,
                phase,
            )


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

    project_id = ECS_PROJECT_ID
    phase = ECS_PHASE
    task_token = ECS_TASK_TOKEN
    customer_feedback = ECS_CUSTOMER_FEEDBACK

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
