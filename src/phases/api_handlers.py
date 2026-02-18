"""API Gateway Lambda handlers for customer-facing endpoints.

Provides project creation, status, deliverables, approval, revision,
and interrupt response endpoints. All handlers share a single Lambda
function with routing based on HTTP method and path.

This module is in phases/ — the ONLY package allowed to import from agents/.
"""

import json
import logging
import uuid
from typing import Any

import boto3

from src.config import (
    AWS_REGION,
    SOW_BUCKET,
    STATE_MACHINE_ARN,
    TASK_LEDGER_TABLE,
)
from src.state.approval import delete_token, get_token
from src.state.interrupts import store_interrupt_response
from src.state.ledger import format_ledger, read_ledger, write_ledger
from src.state.models import TaskLedger

logger = logging.getLogger(__name__)


def _response(status_code: int, body: Any) -> dict[str, Any]:
    """Build an API Gateway proxy response."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body) if not isinstance(body, str) else body,
    }


def create_project_handler(event: dict[str, Any]) -> dict[str, Any]:
    """Create a new project.

    POST /projects
    Body: {project_name, customer, sow_text}

    Creates a task ledger in DynamoDB, uploads SOW to S3, and starts
    the Step Functions state machine.
    """
    body = json.loads(event.get("body", "{}"))
    project_name: str = body.get("project_name", "")
    customer: str = body.get("customer", "")
    sow_text: str = body.get("sow_text", "")

    if not project_name or not sow_text:
        return _response(400, {"error": "project_name and sow_text are required"})

    project_id = str(uuid.uuid4())

    # Create initial task ledger
    ledger = TaskLedger(
        project_id=project_id,
        project_name=project_name,
        customer=customer,
    )
    write_ledger(TASK_LEDGER_TABLE, project_id, ledger)

    # Upload SOW to S3
    if SOW_BUCKET:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        s3.put_object(
            Bucket=SOW_BUCKET,
            Key=f"projects/{project_id}/sow.txt",
            Body=sow_text.encode(),
        )
        logger.info("Uploaded SOW to s3://%s/projects/%s/sow.txt", SOW_BUCKET, project_id)

    # Start Step Functions execution
    if STATE_MACHINE_ARN:
        sfn = boto3.client("stepfunctions", region_name=AWS_REGION)
        sfn.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=f"project-{project_id}",
            input=json.dumps(
                {
                    "project_id": project_id,
                    "project_name": project_name,
                    "sow_text": sow_text,
                }
            ),
        )
        logger.info("Started Step Functions execution for project %s", project_id)

    return _response(
        201,
        {
            "project_id": project_id,
            "project_name": project_name,
            "status": "CREATED",
        },
    )


def project_status_handler(event: dict[str, Any]) -> dict[str, Any]:
    """Get project status.

    GET /projects/{id}/status
    """
    project_id = event.get("pathParameters", {}).get("id", "")
    if not project_id:
        return _response(400, {"error": "project_id is required"})

    ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
    return _response(
        200,
        {
            "project_id": project_id,
            "project_name": ledger.project_name,
            "current_phase": ledger.current_phase.value,
            "phase_status": ledger.phase_status.value,
        },
    )


def project_deliverables_handler(event: dict[str, Any]) -> dict[str, Any]:
    """Get project deliverables.

    GET /projects/{id}/deliverables
    """
    project_id = event.get("pathParameters", {}).get("id", "")
    if not project_id:
        return _response(400, {"error": "project_id is required"})

    ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
    deliverables = {phase: [d.model_dump() for d in items] for phase, items in ledger.deliverables.items()}
    return _response(
        200,
        {
            "project_id": project_id,
            "deliverables": deliverables,
            "summary": format_ledger(ledger),
        },
    )


def approve_handler(event: dict[str, Any]) -> dict[str, Any]:
    """Approve a phase.

    POST /projects/{id}/approve
    Retrieves the stored task token and sends approval to Step Functions.
    """
    project_id = event.get("pathParameters", {}).get("id", "")
    if not project_id:
        return _response(400, {"error": "project_id is required"})

    ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
    phase = ledger.current_phase.value

    task_token = get_token(TASK_LEDGER_TABLE, project_id, phase)
    if not task_token:
        return _response(404, {"error": f"No pending approval for phase {phase}"})

    sfn = boto3.client("stepfunctions", region_name=AWS_REGION)
    sfn.send_task_success(
        taskToken=task_token,
        output=json.dumps({"decision": "APPROVED", "project_id": project_id, "phase": phase}),
    )

    delete_token(TASK_LEDGER_TABLE, project_id, phase)

    return _response(200, {"project_id": project_id, "phase": phase, "decision": "APPROVED"})


def revise_handler(event: dict[str, Any]) -> dict[str, Any]:
    """Request revision for a phase.

    POST /projects/{id}/revise
    Body: {feedback}
    """
    project_id = event.get("pathParameters", {}).get("id", "")
    if not project_id:
        return _response(400, {"error": "project_id is required"})

    body = json.loads(event.get("body", "{}"))
    feedback: str = body.get("feedback", "")
    if not feedback:
        return _response(400, {"error": "feedback is required"})

    ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
    phase = ledger.current_phase.value

    task_token = get_token(TASK_LEDGER_TABLE, project_id, phase)
    if not task_token:
        return _response(404, {"error": f"No pending approval for phase {phase}"})

    sfn = boto3.client("stepfunctions", region_name=AWS_REGION)
    sfn.send_task_success(
        taskToken=task_token,
        output=json.dumps(
            {
                "decision": "REVISION_REQUESTED",
                "feedback": feedback,
                "project_id": project_id,
                "phase": phase,
            }
        ),
    )

    delete_token(TASK_LEDGER_TABLE, project_id, phase)

    return _response(
        200,
        {
            "project_id": project_id,
            "phase": phase,
            "decision": "REVISION_REQUESTED",
        },
    )


def interrupt_respond_handler(event: dict[str, Any]) -> dict[str, Any]:
    """Respond to a mid-phase interrupt.

    POST /projects/{id}/interrupt/{interruptId}/respond
    Body: {response}
    """
    project_id = event.get("pathParameters", {}).get("id", "")
    interrupt_id = event.get("pathParameters", {}).get("interruptId", "")
    if not project_id or not interrupt_id:
        return _response(400, {"error": "project_id and interruptId are required"})

    body = json.loads(event.get("body", "{}"))
    response_text: str = body.get("response", "")
    if not response_text:
        return _response(400, {"error": "response is required"})

    store_interrupt_response(TASK_LEDGER_TABLE, project_id, interrupt_id, response_text)

    return _response(
        200,
        {
            "project_id": project_id,
            "interrupt_id": interrupt_id,
            "status": "ANSWERED",
        },
    )


def route(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Route API Gateway events to the appropriate handler.

    Dispatches based on HTTP method and resource path.

    Args:
        event: API Gateway proxy integration event.
        context: Lambda context (unused).

    Returns:
        API Gateway proxy response dict.
    """
    method = event.get("httpMethod", "")
    resource = event.get("resource", "")

    logger.info("API request: %s %s", method, resource)

    try:
        if method == "POST" and resource == "/projects":
            return create_project_handler(event)
        if method == "GET" and resource == "/projects/{id}/status":
            return project_status_handler(event)
        if method == "GET" and resource == "/projects/{id}/deliverables":
            return project_deliverables_handler(event)
        if method == "POST" and resource == "/projects/{id}/approve":
            return approve_handler(event)
        if method == "POST" and resource == "/projects/{id}/revise":
            return revise_handler(event)
        if method == "POST" and resource == "/projects/{id}/interrupt/{interruptId}/respond":
            return interrupt_respond_handler(event)
        return _response(404, {"error": f"Not found: {method} {resource}"})
    except Exception:
        logger.exception("Handler error: %s %s", method, resource)
        return _response(500, {"error": "Internal server error"})
