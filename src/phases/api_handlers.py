"""API Gateway Lambda handlers for customer-facing endpoints.

Routes to handlers for project creation, status, deliverables, approval,
revision, and interrupt responses. All handlers share a single Lambda
function with routing based on HTTP method and path."""

import json
import logging
import uuid
from typing import Any

import boto3

from src.config import (
    AWS_REGION,
    PM_CHAT_LAMBDA_NAME,
    SOW_BUCKET,
    STATE_MACHINE_ARN,
    TASK_LEDGER_TABLE,
)
from src.phases.artifact_handlers import artifact_content_handler
from src.phases.auth_utils import (
    api_response,
    get_user_id_from_event,
    handle_cors_preflight,
    verify_project_access,
)
from src.phases.middleware import apply_middleware
from src.phases.review_utils import build_review_context
from src.phases.task_handlers import board_tasks_handler
from src.state.approval import delete_token, get_token
from src.state.broadcast import broadcast_to_project
from src.state.chat import get_chat_history, new_message_id, store_chat_message
from src.state.interrupts import store_interrupt_response
from src.state.ledger import format_ledger, read_ledger, write_ledger
from src.state.models import TaskLedger

logger = logging.getLogger(__name__)


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
        return api_response(400, {"error": "project_name and sow_text are required"})

    # Verify user is authenticated
    user_id = get_user_id_from_event(event)
    if not user_id:
        logger.warning("Unauthenticated project creation attempt")
        return api_response(401, {"error": "Authentication required"})

    project_id = str(uuid.uuid4())

    # Create initial task ledger with owner set to authenticated user
    ledger = TaskLedger(
        project_id=project_id,
        project_name=project_name,
        customer=customer,
        owner_id=user_id,
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

    return api_response(
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
        return api_response(400, {"error": "project_id is required"})

    # Verify user has access to this project
    is_authorized, _ = verify_project_access(event, project_id)
    if not is_authorized:
        logger.warning("Unauthorized status access for project=%s", project_id)
        return api_response(403, {"error": "Forbidden"})

    ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
    current_phase = ledger.current_phase.value

    # Build response with review context if awaiting approval
    response_data: dict[str, Any] = {
        "project_id": project_id,
        "project_name": ledger.project_name,
        "current_phase": current_phase,
        "phase_status": ledger.phase_status.value,
    }

    # Add review context when phase is awaiting approval
    if ledger.phase_status.value == "AWAITING_APPROVAL":
        response_data["review_context"] = build_review_context(current_phase)

    return api_response(200, response_data)


def project_deliverables_handler(event: dict[str, Any]) -> dict[str, Any]:
    """Get project deliverables.

    GET /projects/{id}/deliverables
    """
    project_id = event.get("pathParameters", {}).get("id", "")
    if not project_id:
        return api_response(400, {"error": "project_id is required"})

    # Verify user has access to this project
    is_authorized, _ = verify_project_access(event, project_id)
    if not is_authorized:
        logger.warning("Unauthorized deliverables access for project=%s", project_id)
        return api_response(403, {"error": "Forbidden"})

    ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
    deliverables = {phase: [d.model_dump() for d in items] for phase, items in ledger.deliverables.items()}
    return api_response(
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
        return api_response(400, {"error": "project_id is required"})

    # Verify user has access to this project
    is_authorized, _ = verify_project_access(event, project_id)
    if not is_authorized:
        logger.warning("Unauthorized approval attempt for project=%s", project_id)
        return api_response(403, {"error": "Forbidden"})

    ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
    phase = ledger.current_phase.value

    task_token = get_token(TASK_LEDGER_TABLE, project_id, phase)
    if not task_token:
        return api_response(404, {"error": f"No pending approval for phase {phase}"})

    sfn = boto3.client("stepfunctions", region_name=AWS_REGION)
    sfn.send_task_success(
        taskToken=task_token,
        output=json.dumps({"decision": "APPROVED", "project_id": project_id, "phase": phase}),
    )

    delete_token(TASK_LEDGER_TABLE, project_id, phase)

    return api_response(200, {"project_id": project_id, "phase": phase, "decision": "APPROVED"})


def revise_handler(event: dict[str, Any]) -> dict[str, Any]:
    """Request revision for a phase.

    POST /projects/{id}/revise
    Body: {feedback}
    """
    project_id = event.get("pathParameters", {}).get("id", "")
    if not project_id:
        return api_response(400, {"error": "project_id is required"})

    # Verify user has access to this project
    is_authorized, _ = verify_project_access(event, project_id)
    if not is_authorized:
        logger.warning("Unauthorized revision attempt for project=%s", project_id)
        return api_response(403, {"error": "Forbidden"})

    body = json.loads(event.get("body", "{}"))
    feedback: str = body.get("feedback", "")
    if not feedback:
        return api_response(400, {"error": "feedback is required"})

    ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
    phase = ledger.current_phase.value

    task_token = get_token(TASK_LEDGER_TABLE, project_id, phase)
    if not task_token:
        return api_response(404, {"error": f"No pending approval for phase {phase}"})

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

    return api_response(
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
        return api_response(400, {"error": "project_id and interruptId are required"})

    # Verify user has access to this project
    is_authorized, _ = verify_project_access(event, project_id)
    if not is_authorized:
        logger.warning("Unauthorized interrupt response for project=%s", project_id)
        return api_response(403, {"error": "Forbidden"})

    body = json.loads(event.get("body", "{}"))
    response_text: str = body.get("response", "")
    if not response_text:
        return api_response(400, {"error": "response is required"})

    store_interrupt_response(TASK_LEDGER_TABLE, project_id, interrupt_id, response_text)

    return api_response(
        200,
        {
            "project_id": project_id,
            "interrupt_id": interrupt_id,
            "status": "ANSWERED",
        },
    )


def pm_chat_post_handler(event: dict[str, Any]) -> dict[str, Any]:
    """Send a chat message to the PM agent.

    POST /projects/{id}/chat
    Body: {message}

    Stores the customer message, broadcasts it via WebSocket, then
    asynchronously invokes the PM Chat Lambda to generate a streamed
    response.  Returns 202 immediately.
    """
    project_id = event.get("pathParameters", {}).get("id", "")
    if not project_id:
        return api_response(400, {"error": "project_id is required"})

    # Verify user has access to this project
    is_authorized, _ = verify_project_access(event, project_id)
    if not is_authorized:
        logger.warning("Unauthorized chat attempt for project=%s", project_id)
        return api_response(403, {"error": "Forbidden"})

    body = json.loads(event.get("body", "{}"))
    message: str = body.get("message", "")
    if not message:
        return api_response(400, {"error": "message is required"})

    message_id = new_message_id()

    # Read ledger for current phase (also validates project exists)
    ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
    current_phase = ledger.current_phase.value

    # Persist customer message
    store_chat_message(
        TASK_LEDGER_TABLE,
        project_id,
        message_id,
        role="customer",
        content=message,
    )

    # Broadcast customer message to all connected clients
    broadcast_to_project(
        project_id,
        {
            "event": "chat_message",
            "project_id": project_id,
            "phase": current_phase,
            "message_id": message_id,
            "role": "customer",
            "content": message,
        },
    )

    # Async invoke PM Chat Lambda (fire-and-forget)
    if PM_CHAT_LAMBDA_NAME:
        lambda_client = boto3.client("lambda", region_name=AWS_REGION)
        lambda_client.invoke(
            FunctionName=PM_CHAT_LAMBDA_NAME,
            InvocationType="Event",
            Payload=json.dumps(
                {
                    "project_id": project_id,
                    "customer_message": message,
                    "message_id": message_id,
                }
            ),
        )
        logger.info("Async invoked PM chat Lambda for project %s", project_id)

    return api_response(202, {"message_id": message_id})


def pm_chat_get_handler(event: dict[str, Any]) -> dict[str, Any]:
    """Get chat history.

    GET /projects/{id}/chat?limit=50
    """
    project_id = event.get("pathParameters", {}).get("id", "")
    if not project_id:
        return api_response(400, {"error": "project_id is required"})

    # Verify user has access to this project
    is_authorized, _ = verify_project_access(event, project_id)
    if not is_authorized:
        logger.warning("Unauthorized chat history access for project=%s", project_id)
        return api_response(403, {"error": "Forbidden"})

    params = event.get("queryStringParameters") or {}
    try:
        limit = int(params.get("limit", "50"))
    except (ValueError, TypeError):
        limit = 50

    messages = get_chat_history(TASK_LEDGER_TABLE, project_id, limit=limit)
    return api_response(
        200,
        {
            "project_id": project_id,
            "messages": [
                {
                    "message_id": m.message_id,
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp,
                }
                for m in messages
            ],
        },
    )


def upload_url_handler(event: dict[str, Any]) -> dict[str, Any]:
    """Generate a presigned S3 URL for file upload.

    POST /projects/{id}/upload
    Body: {filename, content_type}

    Returns a presigned PUT URL that the client can use to upload
    the file directly to S3.
    """
    project_id = event.get("pathParameters", {}).get("id", "")
    if not project_id:
        return api_response(400, {"error": "project_id is required"})

    body = json.loads(event.get("body", "{}"))
    filename: str = body.get("filename", "")
    content_type: str = body.get("content_type", "application/octet-stream")
    if not filename:
        return api_response(400, {"error": "filename is required"})

    if not SOW_BUCKET:
        return api_response(503, {"error": "Upload storage not configured"})

    file_id = str(uuid.uuid4())
    s3_key = f"projects/{project_id}/uploads/{file_id}_{filename}"

    s3 = boto3.client("s3", region_name=AWS_REGION)
    upload_url = s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": SOW_BUCKET,
            "Key": s3_key,
            "ContentType": content_type,
        },
        ExpiresIn=300,
    )

    return api_response(
        200,
        {
            "upload_url": upload_url,
            "key": s3_key,
            "filename": filename,
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
        if method == "OPTIONS":
            return handle_cors_preflight()

        # Apply middleware (rate limiting, etc.)
        should_continue, error_response = apply_middleware(event)
        if not should_continue:
            return error_response  # type: ignore[return-value]

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
        if method == "POST" and resource == "/projects/{id}/chat":
            return pm_chat_post_handler(event)
        if method == "GET" and resource == "/projects/{id}/chat":
            return pm_chat_get_handler(event)
        if method == "POST" and resource == "/projects/{id}/upload":
            return upload_url_handler(event)
        if method == "GET" and resource == "/projects/{id}/tasks":
            return board_tasks_handler(event)
        if method == "GET" and resource == "/projects/{id}/artifacts":
            return artifact_content_handler(event)
        return api_response(404, {"error": f"Not found: {method} {resource}"})
    except Exception as exc:
        logger.exception("Handler error for %s %s: %s", method, resource, type(exc).__name__)
        return api_response(500, {"error": "Internal server error"})
