"""Shared agent configuration — model definitions and invocation state builder.

This module is imported by individual agent modules (sa.py, pm.py, etc.).
It provides model singletons and the invocation state construction function.
"""

import logging
import os
from typing import Any

import boto3
from botocore.config import Config as BotocoreConfig
from strands.models import BedrockModel

from src.config import (
    ACTIVITY_TABLE,
    AWS_REGION,
    BEDROCK_MAX_RETRIES,
    BEDROCK_READ_TIMEOUT,
    BOARD_TASKS_TABLE,
    KNOWLEDGE_BASE_ID,
    LTM_MEMORY_ID,
    MODEL_ID_OPUS,
    MODEL_ID_SONNET,
    PATTERNS_BUCKET,
    STM_MEMORY_ID,
    TASK_LEDGER_TABLE,
)
from src.state.secrets import get_bedrock_api_key

logger = logging.getLogger(__name__)

# Boto client config — increase read timeout for large model responses
# (Strands default is 120s which is too short for complex architecture docs)
_BEDROCK_CLIENT_CONFIG = BotocoreConfig(
    read_timeout=BEDROCK_READ_TIMEOUT,
    retries={"max_attempts": BEDROCK_MAX_RETRIES},
)


def _get_bedrock_session() -> boto3.Session:
    """Create boto3 session for Bedrock access.

    For cross-account Bedrock API key access, sets the AWS_BEARER_TOKEN_BEDROCK
    environment variable (the mechanism boto3 uses for Bedrock API key auth).
    Falls back to default session (IAM role) if API key is not available.

    Returns:
        boto3.Session configured for Bedrock access.
    """
    api_key = get_bedrock_api_key()
    if api_key:
        # Bedrock API keys use bearer token auth via this env var.
        # The boto3 SDK reads it automatically when calling Bedrock APIs.
        os.environ["AWS_BEARER_TOKEN_BEDROCK"] = api_key
        logger.info("Bedrock API key loaded from Secrets Manager")
    return boto3.Session(region_name=AWS_REGION)


# Model singletons — shared across all agents.
# In tests, patch these at the module level to avoid AWS calls.
_SESSION = _get_bedrock_session()
OPUS = BedrockModel(
    model_id=MODEL_ID_OPUS,
    max_tokens=32_768,
    boto_client_config=_BEDROCK_CLIENT_CONFIG,
    boto_session=_SESSION,
)
SONNET = BedrockModel(
    model_id=MODEL_ID_SONNET,
    max_tokens=16_384,
    boto_client_config=_BEDROCK_CLIENT_CONFIG,
    boto_session=_SESSION,
)


def build_invocation_state(
    project_id: str,
    phase: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Build the invocation_state dict passed to agent calls.

    Validates all fields via the InvocationState Pydantic model, then
    returns a plain dict (since the Strands SDK expects dict[str, Any]).

    Args:
        project_id: Unique project identifier.
        phase: Current delivery phase (e.g., "discovery", "architecture").
        session_id: Optional session ID. Defaults to "{project_id}-{phase}".

    Returns:
        Dict containing all invocation state fields.
    """
    from src.state.models import InvocationState

    state = InvocationState(
        project_id=project_id,
        phase=phase,
        session_id=session_id or f"{project_id}-{phase}",
        task_ledger_table=TASK_LEDGER_TABLE,
        board_tasks_table=BOARD_TASKS_TABLE,
        activity_table=ACTIVITY_TABLE,
        git_repo_url=os.environ.get("PROJECT_REPO_PATH", ""),
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        patterns_bucket=PATTERNS_BUCKET,
        stm_memory_id=STM_MEMORY_ID,
        ltm_memory_id=LTM_MEMORY_ID,
    )
    return state.model_dump()
