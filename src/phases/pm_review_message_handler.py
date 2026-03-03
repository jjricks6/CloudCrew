"""PM Review Message Lambda handler.

Invoked asynchronously when a phase enters/exits review (AWAITING_APPROVAL status).
Generates personalized opening/closing messages from the PM and streams them to
the customer's dashboard via WebSocket. Messages are also persisted to the task
ledger so they survive page reloads.

This module is in phases/ — the ONLY package allowed to import from agents/.
"""

import logging
from collections.abc import Callable
from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.agents.base import build_invocation_state
from src.agents.pm import create_pm_agent
from src.config import AWS_REGION, SOW_BUCKET, TASK_LEDGER_TABLE
from src.state.broadcast import broadcast_to_project
from src.state.ledger import format_ledger, read_ledger, write_ledger

logger = logging.getLogger(__name__)


def _fetch_phase_summary(project_id: str, phase: str) -> str:
    """Fetch the phase summary markdown from S3.

    Args:
        project_id: The project identifier.
        phase: Phase name (e.g., "ARCHITECTURE").

    Returns:
        Phase summary text, or empty string if not found.
    """
    if not SOW_BUCKET:
        logger.warning("SOW_BUCKET not configured, cannot fetch phase summary")
        return ""
    key = f"projects/{project_id}/artifacts/docs/phase-summaries/{phase.lower()}.md"
    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        response = s3.get_object(Bucket=SOW_BUCKET, Key=key)
        return response["Body"].read().decode("utf-8")
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            logger.info("Phase summary not found in S3: s3://%s/%s", SOW_BUCKET, key)
        else:
            logger.exception("S3 error fetching phase summary: s3://%s/%s", SOW_BUCKET, key)
        return ""
    except Exception:
        logger.exception("Failed to fetch phase summary from S3: s3://%s/%s", SOW_BUCKET, key)
        return ""


def _make_ws_callback(project_id: str, message_type: str) -> Callable[..., None]:
    """Create a Strands callback_handler that broadcasts review message chunks.

    Args:
        project_id: The project to broadcast to.
        message_type: "opening" or "closing".

    Returns:
        A callback function suitable for ``Agent.callback_handler``.
    """

    def callback(*, data: str = "", complete: bool = False, **kwargs: Any) -> None:
        if data:
            broadcast_to_project(
                project_id,
                {
                    "event": "review_message",
                    "project_id": project_id,
                    "message_type": message_type,
                    "content": data,
                },
            )

    return callback


def _build_opening_message_prompt(phase: str, ledger: Any, phase_summary: str) -> str:
    """Build prompt for PM to generate opening review message.

    Args:
        phase: The phase name (e.g., "ARCHITECTURE").
        ledger: The task ledger with project context.
        phase_summary: The phase summary markdown (may be empty).

    Returns:
        The prompt string.
    """
    ledger_summary = format_ledger(ledger)
    summary_block = f"## Phase Summary\n{phase_summary}" if phase_summary else "*(Phase summary not yet available.)*"
    return f"""You are welcoming the customer to the {phase} phase review.

## Project Context
{ledger_summary}

{summary_block}

Generate a warm, professional welcome message (2-3 paragraphs) that:
1. Congratulates them on completing the {phase} phase
2. Highlights 2-3 specific accomplishments from this phase (reference the summary)
3. Explains what artifacts are ready for review
4. Invites them to ask questions or request changes

Be conversational and personable. Use markdown formatting where appropriate.
Focus on their specific work, not generic praise."""


def _build_closing_message_prompt(phase: str, ledger: Any, phase_summary: str) -> str:
    """Build prompt for PM to generate closing review message.

    Args:
        phase: The phase name (e.g., "ARCHITECTURE").
        ledger: The task ledger with project context.
        phase_summary: The phase summary markdown (may be empty).

    Returns:
        The prompt string.
    """
    ledger_summary = format_ledger(ledger)
    summary_block = f"## Phase Summary\n{phase_summary}" if phase_summary else "*(Phase summary not yet available.)*"
    return f"""The customer has approved the {phase} phase.

## Project Context
{ledger_summary}

{summary_block}

Generate a brief thank you message (1-2 paragraphs) that:
1. Thanks them for their review and approval
2. Confirms what happens next (proceeding to the next phase or completing engagement)
3. Reassures them about continued progress and quality

Be warm and professional. Use markdown formatting.
Reference the specific work completed in this phase."""


def _persist_review_message(project_id: str, message_type: str, content: str) -> None:
    """Persist the generated review message to the task ledger.

    Args:
        project_id: The project identifier.
        message_type: "opening" or "closing".
        content: The generated message text.
    """
    try:
        ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
        if message_type == "opening":
            ledger.review_opening_message = content
        else:
            ledger.review_closing_message = content
        write_ledger(TASK_LEDGER_TABLE, project_id, ledger)
        logger.info("Persisted %s review message for project=%s", message_type, project_id)
    except Exception:
        logger.exception(
            "Failed to persist %s review message for project=%s",
            message_type,
            project_id,
        )


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Generate and stream a review message from PM.

    Expected event payload::

        {
            "project_id": "...",
            "phase": "ARCHITECTURE",
            "message_type": "opening" | "closing"
        }

    The handler:
    1. Loads project context (ledger) and fetches phase summary from S3.
    2. Broadcasts a ``review_message_thinking`` event.
    3. Creates a PM agent with a streaming callback.
    4. Invokes the agent — tokens are broadcast as ``review_message`` events.
    5. Persists the generated message to the task ledger for later retrieval.
    6. Broadcasts ``review_message_complete`` and logs completion.

    Args:
        event: Async invocation payload.
        context: Lambda context (unused).

    Returns:
        Dict with message_type and status.
    """
    project_id: str = event["project_id"]
    phase: str = event["phase"]
    message_type: str = event.get("message_type", "opening")

    logger.info(
        "PM review message handler invoked for project=%s, phase=%s, type=%s",
        project_id,
        phase,
        message_type,
    )

    try:
        # 1. Load project context
        ledger = read_ledger(TASK_LEDGER_TABLE, project_id)

        # 2. Fetch phase summary from S3 (so PM doesn't need git_read)
        phase_summary = _fetch_phase_summary(project_id, phase)

        # 3. Broadcast thinking indicator
        broadcast_to_project(
            project_id,
            {
                "event": "review_message_thinking",
                "project_id": project_id,
                "message_type": message_type,
            },
        )

        # 4. Create PM agent with streaming callback
        pm = create_pm_agent()
        pm.callback_handler = _make_ws_callback(project_id, message_type)

        invocation_state = build_invocation_state(
            project_id=project_id,
            phase=phase.lower(),
        )

        # 5. Build prompt based on message type
        if message_type == "opening":
            task = _build_opening_message_prompt(phase, ledger, phase_summary)
        else:
            task = _build_closing_message_prompt(phase, ledger, phase_summary)

        # 6. Invoke PM — callback fires per token
        try:
            result = pm(task, invocation_state=invocation_state)
            response_text = str(result)
        except Exception as e:
            # Broad catch needed: Strands agents may raise various exceptions
            logger.exception(
                "PM agent failed for project=%s, phase=%s: %s",
                project_id,
                phase,
                type(e).__name__,
            )
            response_text = (
                f"I encountered an error generating the {message_type} message. Please refresh and try again."
            )
            broadcast_to_project(
                project_id,
                {
                    "event": "review_message",
                    "project_id": project_id,
                    "message_type": message_type,
                    "content": response_text,
                },
            )

        # 7. Persist the generated message to the task ledger
        _persist_review_message(project_id, message_type, response_text)

        # 8. Broadcast done
        broadcast_to_project(
            project_id,
            {
                "event": "review_message_complete",
                "project_id": project_id,
                "message_type": message_type,
                "length": len(response_text),
            },
        )

        logger.info(
            "PM review message complete for project=%s, type=%s, length=%d",
            project_id,
            message_type,
            len(response_text),
        )

        return {
            "status": "success",
            "project_id": project_id,
            "message_type": message_type,
            "length": len(response_text),
        }

    except Exception as e:
        logger.exception(
            "Unexpected error in PM review message handler for project=%s: %s",
            project_id,
            str(e),
        )
        return {
            "status": "error",
            "project_id": project_id,
            "message_type": message_type,
            "error": str(e),
        }
