"""Pydantic data models for CloudCrew state.

Shared types used across modules. This module imports only from config — never
from agents/, tools/, hooks/, or phases/.
"""

from enum import StrEnum

from pydantic import BaseModel, Field

# --- Enums ---


class Phase(StrEnum):
    """Project delivery phases."""

    DISCOVERY = "DISCOVERY"
    ARCHITECTURE = "ARCHITECTURE"
    POC = "POC"
    PRODUCTION = "PRODUCTION"
    HANDOFF = "HANDOFF"
    RETROSPECTIVE = "RETROSPECTIVE"


class PhaseStatus(StrEnum):
    """Status of the current phase."""

    IN_PROGRESS = "IN_PROGRESS"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REVISION_REQUESTED = "REVISION_REQUESTED"


# --- Task Ledger Entry Models ---


class Fact(BaseModel):
    """A verified piece of information about the project."""

    description: str
    source: str
    timestamp: str


class Assumption(BaseModel):
    """An unverified assumption that needs validation."""

    description: str
    confidence: str = Field(description="HIGH, MEDIUM, or LOW")
    timestamp: str


class Decision(BaseModel):
    """A project or technical decision with rationale."""

    description: str
    rationale: str
    made_by: str
    timestamp: str
    adr_path: str = ""


class Blocker(BaseModel):
    """An issue blocking progress."""

    description: str
    assigned_to: str
    status: str = Field(description="OPEN or RESOLVED")
    timestamp: str


class DeliverableItem(BaseModel):
    """A deliverable artifact within a phase."""

    name: str
    git_path: str
    status: str = Field(description="IN_PROGRESS, COMPLETE, or NEEDS_REVISION")


# --- Task Ledger ---


class TaskLedger(BaseModel):
    """Structured project state stored in DynamoDB.

    Maintained by the PM agent. All agents can read it.
    Inspired by Magentic-One's research on preventing context drift.
    """

    project_id: str
    project_name: str = ""
    customer: str = ""
    current_phase: Phase = Phase.DISCOVERY
    phase_status: PhaseStatus = PhaseStatus.IN_PROGRESS
    facts: list[Fact] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    blockers: list[Blocker] = Field(default_factory=list)
    deliverables: dict[str, list[DeliverableItem]] = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


# --- SOW Parsing ---


class ParsedSOW(BaseModel):
    """Structured requirements extracted from a Statement of Work."""

    objectives: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    timeline: str = ""


# --- Board Tasks (Kanban) ---


class TaskComment(BaseModel):
    """A comment on a board task, added by an agent."""

    author: str
    content: str
    timestamp: str


class BoardTask(BaseModel):
    """A granular work item on the kanban board.

    Created and managed by agents during phase execution. Separate from
    deliverables — tasks are work items, deliverables are artifacts.
    """

    task_id: str
    title: str
    description: str
    phase: str
    status: str = Field(description="backlog | in_progress | review | done")
    assigned_to: str
    comments: list[TaskComment] = Field(default_factory=list)
    artifact_path: str = ""
    created_at: str = ""
    updated_at: str = ""


# --- Invocation State ---


class ApprovalToken(BaseModel):
    """A stored Step Functions task token awaiting customer approval."""

    project_id: str
    phase: str
    task_token: str
    created_at: str = ""


class InterruptRecord(BaseModel):
    """A mid-phase interrupt requiring customer input."""

    project_id: str
    interrupt_id: str
    question: str
    response: str = ""
    status: str = Field(description="PENDING or ANSWERED")
    created_at: str = ""
    answered_at: str = ""


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
    board_tasks_table: str = Field(default="", description="DynamoDB table for board tasks")
    stm_memory_id: str = Field(default="", description="AgentCore Memory ID for short-term memory")
    ltm_memory_id: str = Field(default="", description="AgentCore Memory ID for long-term memory")
