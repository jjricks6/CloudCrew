"""PM Review Lambda handler.

After a phase Swarm completes, Step Functions invokes this Lambda to run
the PM agent in standalone mode. The PM reviews deliverables, validates
against SOW acceptance criteria, and updates the task ledger.

This module is in phases/ — the ONLY package allowed to import from agents/.
"""

import logging
from typing import Any

from src.agents.base import build_invocation_state
from src.agents.pm import create_pm_agent
from src.config import TASK_LEDGER_TABLE
from src.state.ledger import format_ledger, read_ledger

logger = logging.getLogger(__name__)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Run PM agent to review phase deliverables.

    Creates a standalone PM agent (not a Swarm) and asks it to review
    the deliverables from the completed phase. The PM reads deliverables
    via git_read, validates against SOW acceptance criteria, and updates
    the task ledger.

    Args:
        event: Contains project_id, phase, phase_result.
        context: Lambda context (unused).

    Returns:
        Dict with review results (project_id, phase, review_passed,
        deliverable_package).
    """
    project_id: str = event["project_id"]
    phase: str = event["phase"]

    logger.info("PM reviewing deliverables for project=%s, phase=%s", project_id, phase)

    # Read current task ledger for context
    ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
    ledger_summary = format_ledger(ledger)

    # Build invocation state for the PM agent
    invocation_state = build_invocation_state(
        project_id=project_id,
        phase=phase.lower(),
    )

    # Create PM agent in standalone mode
    pm = create_pm_agent()

    review_task = (
        f"You are reviewing the deliverables from the {phase} phase.\n\n"
        f"Current task ledger:\n{ledger_summary}\n\n"
        f"Review all deliverables for this phase:\n"
        f"1. Read each deliverable file using git_read\n"
        f"2. Validate against SOW acceptance criteria\n"
        f"3. Update the task ledger with your review findings\n"
        f"4. Conclude with a clear PASS or FAIL verdict\n\n"
        f"If deliverables meet acceptance criteria, respond with 'REVIEW: PASSED'.\n"
        f"If not, respond with 'REVIEW: FAILED' and list the specific issues."
    )

    # Invoke PM agent directly (not a Swarm)
    result = pm(review_task, invocation_state=invocation_state)

    # Parse the PM's verdict from the response
    response_text = str(result)
    review_passed = "REVIEW: PASSED" in response_text.upper()

    logger.info(
        "PM review %s for project=%s, phase=%s",
        "PASSED" if review_passed else "FAILED",
        project_id,
        phase,
    )

    # Read updated deliverables from ledger
    updated_ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
    deliverable_package = {
        phase: [d.model_dump() for d in updated_ledger.deliverables.get(phase, [])],
    }

    return {
        "project_id": project_id,
        "phase": phase,
        "review_passed": review_passed,
        "deliverable_package": deliverable_package,
    }
