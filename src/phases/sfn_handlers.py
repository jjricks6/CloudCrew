"""Step Functions integration Lambda handlers.

start_phase_handler: Launches an ECS Fargate task for phase execution.
store_approval_token_handler: Stores a task token for customer approval.

This module is in phases/ — the ONLY package allowed to import from agents/.
"""

import logging
from typing import Any

import boto3

from src.config import (
    AWS_REGION,
    ECS_CLUSTER_ARN,
    ECS_SECURITY_GROUP,
    ECS_SUBNETS,
    ECS_TASK_DEFINITION,
    TASK_LEDGER_TABLE,
)
from src.state.approval import store_token
from src.state.broadcast import broadcast_to_project

logger = logging.getLogger(__name__)


def start_phase_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Launch an ECS Fargate task to execute a project phase.

    Called by Step Functions via ``lambda:invoke.waitForTaskToken``.
    Step Functions waits for the ECS task to call SendTaskSuccess.

    Updates the task ledger to reflect the new phase/status before
    launching the ECS task, ensuring the customer status API returns
    the correct state immediately.

    Args:
        event: Contains project_id, phase, task_token, customer_feedback.
        context: Lambda context (unused).

    Returns:
        Dict with ecs_task_arn for tracking.

    Raises:
        RuntimeError: If ECS fails to launch the task.
    """
    project_id: str = event["project_id"]
    phase: str = event["phase"]
    task_token: str = event["task_token"]
    customer_feedback: str = event.get("customer_feedback", "")

    logger.info("Starting ECS task for project=%s, phase=%s", project_id, phase)

    # Update task ledger to reflect the new phase — critical for customer
    # status polling to show the correct phase immediately.
    from src.state.ledger import read_ledger, write_ledger
    from src.state.models import Phase, PhaseStatus

    ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
    ledger.current_phase = Phase(phase)
    ledger.phase_status = PhaseStatus.IN_PROGRESS
    write_ledger(TASK_LEDGER_TABLE, project_id, ledger)

    # Broadcast phase_started event to connected dashboard clients
    broadcast_to_project(
        project_id,
        {
            "event": "phase_started",
            "project_id": project_id,
            "phase": phase,
            "status": "IN_PROGRESS",
        },
    )

    ecs = boto3.client("ecs", region_name=AWS_REGION)

    subnets = [s.strip() for s in ECS_SUBNETS.split(",") if s.strip()]

    response = ecs.run_task(
        cluster=ECS_CLUSTER_ARN,
        taskDefinition=ECS_TASK_DEFINITION,
        launchType="FARGATE",
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": subnets,
                "securityGroups": [ECS_SECURITY_GROUP],
                "assignPublicIp": "ENABLED",
            },
        },
        overrides={
            "containerOverrides": [
                {
                    "name": "phase-runner",
                    "environment": [
                        {"name": "PROJECT_ID", "value": project_id},
                        {"name": "PHASE", "value": phase},
                        {"name": "TASK_TOKEN", "value": task_token},
                        {"name": "CUSTOMER_FEEDBACK", "value": customer_feedback},
                    ],
                },
            ],
        },
    )

    # Check for ECS launch failures — if no tasks started, Step Functions
    # would wait indefinitely for a SendTaskSuccess that never comes.
    tasks = response.get("tasks", [])
    failures = response.get("failures", [])

    if not tasks:
        failure_reasons = "; ".join(f.get("reason", "unknown") for f in failures)
        msg = f"ECS RunTask returned no tasks. Failures: {failure_reasons}"
        logger.error(msg)
        raise RuntimeError(msg)

    task_arn = tasks[0]["taskArn"]
    logger.info("ECS task launched: %s", task_arn)
    return {"ecs_task_arn": task_arn, "project_id": project_id, "phase": phase}


def store_approval_token_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Store a Step Functions task token for customer approval.

    Called by Step Functions via ``lambda:invoke.waitForTaskToken``.
    The token is stored in DynamoDB so the customer API can retrieve it
    when the customer approves or requests revision.

    Args:
        event: Contains project_id, phase, task_token.
        context: Lambda context (unused).

    Returns:
        Dict confirming token storage.
    """
    project_id: str = event["project_id"]
    phase: str = event["phase"]
    task_token: str = event["task_token"]

    logger.info("Storing approval token for project=%s, phase=%s", project_id, phase)

    store_token(TASK_LEDGER_TABLE, project_id, phase, task_token)

    # Update task ledger phase status to AWAITING_APPROVAL
    from src.state.ledger import read_ledger, write_ledger
    from src.state.models import PhaseStatus

    ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
    ledger.phase_status = PhaseStatus.AWAITING_APPROVAL
    write_ledger(TASK_LEDGER_TABLE, project_id, ledger)

    # Broadcast awaiting_approval event to connected dashboard clients
    broadcast_to_project(
        project_id,
        {
            "event": "awaiting_approval",
            "project_id": project_id,
            "phase": phase,
        },
    )

    return {
        "project_id": project_id,
        "phase": phase,
        "status": "TOKEN_STORED",
    }


def route(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Route to the appropriate handler based on event action.

    Args:
        event: Must contain an "action" field.
        context: Lambda context.

    Returns:
        Response dict from the handler.
    """
    action = event.get("action", "")
    if action == "start_phase":
        return start_phase_handler(event, context)
    if action == "store_approval_token":
        return store_approval_token_handler(event, context)
    return {"error": f"Unknown action: {action}"}
