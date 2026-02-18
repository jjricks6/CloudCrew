"""Step Functions integration Lambda handlers.

start_phase_handler: Launches an ECS Fargate task for phase execution.
store_approval_token_handler: Stores a task token for customer approval.

This module is in phases/ — the ONLY package allowed to import from agents/.
"""

import json
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

logger = logging.getLogger(__name__)


def start_phase_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Launch an ECS Fargate task to execute a project phase.

    Called by Step Functions via ``lambda:invoke.waitForTaskToken``.
    Step Functions waits for the ECS task to call SendTaskSuccess.

    Args:
        event: Contains project_id, phase, task_token, customer_feedback.
        context: Lambda context (unused).

    Returns:
        Dict with ecs_task_arn for tracking.
    """
    project_id: str = event["project_id"]
    phase: str = event["phase"]
    task_token: str = event["task_token"]
    customer_feedback: str = event.get("customer_feedback", "")

    logger.info("Starting ECS task for project=%s, phase=%s", project_id, phase)

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

    tasks = response.get("tasks", [])
    task_arn = tasks[0]["taskArn"] if tasks else "unknown"

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

    return {
        "project_id": project_id,
        "phase": phase,
        "status": "TOKEN_STORED",
    }


def route(event: dict[str, Any], context: Any) -> str:
    """Route to the appropriate handler based on event action.

    Args:
        event: Must contain an "action" field.
        context: Lambda context.

    Returns:
        JSON-encoded response from the handler.
    """
    action = event.get("action", "")
    if action == "start_phase":
        result = start_phase_handler(event, context)
    elif action == "store_approval_token":
        result = store_approval_token_handler(event, context)
    else:
        result = {"error": f"Unknown action: {action}"}
    return json.dumps(result)
