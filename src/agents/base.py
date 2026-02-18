"""Shared agent configuration — model definitions and invocation state builder.

This module is imported by individual agent modules (sa.py, pm.py, etc.).
It provides model singletons and the invocation state construction function.
"""

from typing import Any

from botocore.config import Config as BotocoreConfig
from strands.models import BedrockModel

from src.config import (
    BEDROCK_MAX_RETRIES,
    BEDROCK_READ_TIMEOUT,
    KNOWLEDGE_BASE_ID,
    LTM_MEMORY_ID,
    MODEL_ID_OPUS,
    MODEL_ID_SONNET,
    PATTERNS_BUCKET,
    PROJECT_REPO_PATH,
    STM_MEMORY_ID,
    TASK_LEDGER_TABLE,
)

# Boto client config — increase read timeout for large model responses
# (Strands default is 120s which is too short for complex architecture docs)
_BEDROCK_CLIENT_CONFIG = BotocoreConfig(
    read_timeout=BEDROCK_READ_TIMEOUT,
    retries={"max_attempts": BEDROCK_MAX_RETRIES},
)

# Model singletons — shared across all agents.
# In tests, patch these at the module level to avoid AWS calls.
OPUS = BedrockModel(model_id=MODEL_ID_OPUS, boto_client_config=_BEDROCK_CLIENT_CONFIG)
SONNET = BedrockModel(model_id=MODEL_ID_SONNET, boto_client_config=_BEDROCK_CLIENT_CONFIG)


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
        git_repo_url=PROJECT_REPO_PATH,
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        patterns_bucket=PATTERNS_BUCKET,
        stm_memory_id=STM_MEMORY_ID,
        ltm_memory_id=LTM_MEMORY_ID,
    )
    return state.model_dump()
