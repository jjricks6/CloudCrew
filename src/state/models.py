"""Pydantic data models for CloudCrew state.

Shared types used across modules. This module imports only from config — never
from agents/, tools/, hooks/, or phases/.
"""

from pydantic import BaseModel, Field


class InvocationState(BaseModel):
    """State passed to every agent invocation via invocation_state kwarg.

    Constructed by build_invocation_state() in agents/base.py and accessed
    by tools via tool_context.invocation_state.
    """

    project_id: str = Field(description="Unique project identifier")
    phase: str = Field(description="Current delivery phase")
    session_id: str = Field(description="Unique session identifier for this invocation")
    task_ledger_table: str = Field(description="DynamoDB table name for the task ledger")
    git_repo_url: str = Field(description="Local path to the project Git repository")
    knowledge_base_id: str = Field(description="Bedrock Knowledge Base ID for project artifacts")
    patterns_bucket: str = Field(description="S3 bucket name for the pattern library")
