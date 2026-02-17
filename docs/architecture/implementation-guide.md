# Implementation Guide

> Step-by-step build plan for CloudCrew.
> Last updated: 2026-02-17

---

## Build Order

The implementation is organized into 6 milestones. Each builds on the previous and produces a testable system.

---

### Milestone 1: Single Agent Foundation

**Goal:** Get one agent working end-to-end with tools, memory, and artifact production.

**Build:**

#### 1.1 Project Structure

Set up the Python project with Strands SDK dependency. Create the repo structure:

```
cloudcrew/
├── src/
│   ├── agents/           # Agent definitions
│   │   ├── __init__.py
│   │   ├── base.py       # Shared agent configuration
│   │   ├── pm.py         # PM agent
│   │   ├── sa.py         # SA agent
│   │   ├── infra.py      # Infra agent
│   │   ├── dev.py        # Dev agent
│   │   ├── data.py       # Data agent
│   │   ├── security.py   # Security agent
│   │   └── qa.py         # QA agent
│   ├── tools/            # Custom tools
│   │   ├── __init__.py
│   │   ├── git_tools.py  # Scoped Git read/write
│   │   ├── sow_parser.py # SOW parsing tool
│   │   ├── task_ledger.py# DynamoDB task ledger tools
│   │   ├── diagrams.py   # Architecture diagram generation
│   │   ├── adr_writer.py # ADR generation tool
│   │   ├── terraform.py  # Terraform gen/validate/plan
│   │   ├── security_scan.py # Checkov, tfsec, OWASP
│   │   ├── code_tools.py # Code gen/edit/lint/test
│   │   ├── data_tools.py # Schema design, queries, pipelines
│   │   └── kb_search.py  # Knowledge Base search wrapper
│   ├── hooks/            # Custom hooks
│   │   ├── __init__.py
│   │   ├── approval.py   # Approval gate hook
│   │   ├── memory.py     # Memory management hook
│   │   └── budget.py     # Token budget tracking hook
│   ├── templates/        # Artifact templates
│   │   ├── adr.md
│   │   ├── architecture_doc.md
│   │   ├── phase_summary.md
│   │   ├── security_review.md
│   │   ├── test_plan.md
│   │   └── project_plan.md
│   ├── state/            # State management
│   │   ├── __init__.py
│   │   ├── task_ledger.py# DynamoDB operations
│   │   └── models.py     # Data models (Pydantic)
│   ├── phases/           # Phase orchestration
│   │   ├── __init__.py
│   │   ├── discovery.py  # Discovery phase Swarm setup
│   │   ├── architecture.py
│   │   ├── poc.py
│   │   ├── production.py
│   │   └── handoff.py
│   └── config.py         # Configuration (models, memory IDs, etc.)
├── infra/
│   └── terraform/        # CloudCrew's own infrastructure
│       ├── dynamodb.tf
│       ├── step_functions.tf
│       ├── ecs.tf        # Fargate cluster + task defs for phase execution
│       ├── ecr.tf        # Container registry for phase runner image
│       ├── lambda.tf     # PM review, approval API, chat handlers
│       ├── api_gateway.tf # REST + WebSocket APIs
│       ├── cognito.tf
│       ├── s3.tf         # SOW uploads, KB data source
│       └── variables.tf
├── dashboard/            # React SPA
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── api/
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── pyproject.toml
└── README.md
```

#### 1.2 Base Agent Configuration

Create `src/agents/base.py` with shared config:

```python
from strands import Agent
from strands.models.bedrock import BedrockModel

# Model definitions
OPUS = BedrockModel(model_id="us.anthropic.claude-opus-4-6-v1")
SONNET = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514")

# Shared invocation state builder
def build_invocation_state(project_id: str, phase: str, session_id: str = None) -> dict:
    return {
        "project_id": project_id,
        "phase": phase,
        "session_id": session_id or f"{project_id}-{phase}",
        "task_ledger_table": os.environ["TASK_LEDGER_TABLE"],
        "git_repo_url": os.environ["PROJECT_REPO_URL"],
        "knowledge_base_id": os.environ["KNOWLEDGE_BASE_ID"],
    }
```

#### 1.3 Git Tools

Implement scoped Git tools. Each agent gets a tool that can only write to its designated directories:

```python
from strands import tool

@tool
def git_write_architecture(file_path: str, content: str) -> str:
    """Write a file to docs/architecture/ in the project repo."""
    if not file_path.startswith("docs/architecture/"):
        return "Error: SA agent can only write to docs/architecture/"
    # Clone/pull repo, write file, commit, push
    ...

@tool
def git_write_infra(file_path: str, content: str) -> str:
    """Write a file to infra/ in the project repo."""
    if not file_path.startswith("infra/"):
        return "Error: Infra agent can only write to infra/"
    ...

@tool
def git_read(file_path: str) -> str:
    """Read any file from the project repo."""
    ...
```

#### 1.4 SA Agent

Implement the SA agent with diagram and ADR tools. Test it independently:

```python
from src.agents.base import OPUS
from src.tools.git_tools import git_read, git_write_architecture
from src.tools.diagrams import generate_diagram
from src.tools.adr_writer import write_adr
from src.tools.kb_search import knowledge_base_search

sa = Agent(
    name="sa",
    model=OPUS,
    system_prompt=SA_SYSTEM_PROMPT,
    tools=[generate_diagram, write_adr, aws_service_lookup,
           git_read, git_write_architecture, knowledge_base_search,
           read_task_ledger]
)

# Test independently
result = sa("Design a serverless API for a todo application on AWS")
```

#### 1.5 Verify

SA agent can produce an architecture doc and ADR in the Git repo.

**Test:** Manually invoke the SA agent with a simple architecture task. Verify it produces a valid architecture document and ADR following the templates.

---

### Milestone 2: Two-Agent Swarm

**Goal:** Get two agents collaborating in a Swarm with handoffs and review cycles.

**Build:**

#### 2.1 Infra Agent

Implement with Terraform tools and Checkov scanning.

#### 2.2 Security Agent

Implement with security scanning tools.

#### 2.3 Architecture Swarm

Create a Swarm with SA + Infra + Security:

```python
from strands.multiagent import Swarm

architecture_swarm = Swarm(
    [sa_agent, infra_agent, security_agent],
    entry_point=sa_agent,
    max_handoffs=15,
    max_iterations=15,
    execution_timeout=1200,
    node_timeout=300,
    repetitive_handoff_detection_window=8,
    repetitive_handoff_min_unique_agents=3
)

result = architecture_swarm(
    "Design the architecture for a serverless e-commerce API with DynamoDB, Lambda, and API Gateway",
    invocation_state={"project_id": "test-001", "phase": "architecture"}
)
```

#### 2.4 Verify the Review Cycle

SA designs → hands off to Infra for IaC → Infra writes Terraform → hands off to Security for review → Security reviews and hands back findings → Infra fixes → Security re-reviews.

#### 2.5 Measure

Track handoff count, total tokens, execution time, context growth per handoff.

**Test:** Run the Architecture Swarm on 3 different architecture tasks of increasing complexity. Verify:

- All three agents participate
- Review handoffs happen (Security reviews Infra's work)
- Artifacts are produced in the correct Git directories
- No repetitive handoff loops

---

### Milestone 3: Task Ledger + Memory

**Goal:** Add state management and memory so agents have context across interactions.

**Build:**

#### 3.1 DynamoDB Table

Create the `cloudcrew-projects` table with the task ledger schema (see [final-architecture.md](final-architecture.md#task-ledger-schema-dynamodb)).

#### 3.2 Task Ledger Tools

`update_task_ledger` (PM only) and `read_task_ledger` (all agents):

```python
@tool(context=True)
def read_task_ledger(tool_context: ToolContext) -> str:
    """Read the current project task ledger."""
    project_id = tool_context.invocation_state.get("project_id")
    # Read from DynamoDB and return formatted ledger
    ...

@tool(context=True)
def update_task_ledger(
    section: str,
    entry: dict,
    tool_context: ToolContext
) -> str:
    """Update a section of the task ledger. PM agent only.

    Args:
        section: One of 'facts', 'assumptions', 'decisions', 'blockers', 'deliverables'
        entry: The entry to add/update
    """
    project_id = tool_context.invocation_state.get("project_id")
    # Write to DynamoDB
    ...
```

#### 3.3 PM Agent

Implement with SOW parser and task ledger tools.

#### 3.4 SOW Parser Tool

Takes document content, extracts structured requirements:

```python
@tool
def parse_sow(document_content: str) -> dict:
    """Parse a Statement of Work and extract structured requirements.

    Returns JSON with: objectives, requirements, constraints,
    deliverables, acceptance_criteria, timeline
    """
    # Use a secondary LLM call to extract structured data
    ...
```

#### 3.5 AgentCore Memory Setup

Create memory resources:

```python
# STM — per-agent session memory
stm = memory_client.create_memory_and_wait(
    name="CloudCrew_STM",
    strategies=[],
    event_expiry_days=7
)

# LTM — shared project memory with extraction
ltm = memory_client.create_memory_and_wait(
    name="CloudCrew_LTM",
    strategies=[
        {"semanticMemoryStrategy": {
            "name": "decisions",
            "namespaces": ["/decisions/"]
        }},
        {"userPreferenceMemoryStrategy": {
            "name": "preferences",
            "namespaces": ["/customer/preferences/"]
        }},
        {"summaryMemoryStrategy": {
            "name": "summaries",
            "namespaces": ["/summaries/{actorId}/{sessionId}"]
        }}
    ],
    event_expiry_days=90
)
```

#### 3.6 Memory Hooks

Hook-based memory integration for loading/saving context:

```python
from strands.agent.hooks import HookProvider, HookRegistry
from strands.types.event import BeforeInvocationEvent, AfterInvocationEvent

class MemoryHook(HookProvider):
    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeInvocationEvent, self.load_context)
        registry.add_callback(AfterInvocationEvent, self.save_context)

    def load_context(self, event: BeforeInvocationEvent) -> None:
        # Load relevant LTM context
        # Inject into agent's system prompt or invocation_state
        ...

    def save_context(self, event: AfterInvocationEvent) -> None:
        # Save conversation to STM
        ...
```

#### 3.7 Discovery Swarm

PM + SA collaborating on requirements. Note the reduced limits for a 2-agent Swarm:

```python
discovery_swarm = Swarm(
    [pm_agent, sa_agent],
    entry_point=pm_agent,
    max_handoffs=10,
    max_iterations=10,
    execution_timeout=900,   # 15 min — smaller scope
    node_timeout=300,
    repetitive_handoff_detection_window=6,
    repetitive_handoff_min_unique_agents=2,  # Only 2 agents available
)

result = discovery_swarm(
    "Here is the SOW: [SOW content]",
    invocation_state=build_invocation_state("proj-001", "discovery")
)
```

**Test:**

- PM parses a sample SOW, creates task ledger, hands off to SA for initial architecture
- Verify task ledger is populated with facts, assumptions, and decisions
- Verify SA can read the task ledger to understand requirements
- Verify memory persists across separate invocations

---

### Milestone 4: Step Functions + Approval Gates

**Goal:** Full phase orchestration with durable HITL approval gates.

**Build:**

#### 4.1 Step Functions State Machine

Define in Terraform:

```
Discovery Swarm (ECS) → PM Review (Lambda) → ApprovalGate (waitForTaskToken)
  → Architecture Swarm (ECS) → PM Review → ApprovalGate
  → POC Swarm (ECS) → PM Review → ApprovalGate
  → Production Swarm (ECS) → PM Review → ApprovalGate
  → Handoff Swarm (ECS) → Complete
```

Each phase state:
- Invokes an **ECS Fargate task** that runs the appropriate Swarm (not Lambda — Swarm timeouts exceed Lambda's 15-min limit, and interrupt blocking requires a long-lived process)
- Passes project_id, phase context, and any customer feedback from previous approval

PM Review step (after each Swarm):
- Invokes a Lambda that runs a standalone PM agent
- PM reads deliverables from Git, validates against SOW, updates task ledger
- For Discovery and Handoff (where PM is already in the Swarm), this step is lighter — just formats the deliverable package

Each approval gate:
- Uses `waitForTaskToken` — a Lambda stores the task token in DynamoDB
- Waits for external signal (customer approval via API)

Error handling at each phase:
- ECS task failure → retry 1x → mark FAILED, notify customer
- Swarm timeout → retry 1x with extended timeout → mark FAILED
- Step Functions `Catch` block on each state routes to an error handler

#### 4.2 Phase ECS Task

ECS Fargate task (Docker container) that:

1. Receives phase name + project context from Step Functions (via environment variables or S3 input)
2. Creates the appropriate Swarm (based on phase → agent mapping)
3. Runs the Swarm
4. Handles Strands interrupts:
   - When interrupt occurs, publishes question to customer dashboard via WebSocket (API Gateway)
   - **Blocks** waiting for response (ECS has no timeout ceiling)
   - When customer responds via API, the response is written to a DynamoDB record
   - ECS task polls for the response, then resumes Swarm with `InterruptResponseContent`
5. Returns phase result to Step Functions via `SendTaskSuccess`

```python
def main():
    """ECS task entrypoint for phase execution."""
    project_id = os.environ["PROJECT_ID"]
    phase = os.environ["PHASE"]
    task_token = os.environ["TASK_TOKEN"]
    customer_feedback = json.loads(os.environ.get("CUSTOMER_FEEDBACK", "null"))

    # Build Swarm for this phase
    swarm = build_phase_swarm(phase)

    # Build task with context
    task = build_phase_task(project_id, phase, customer_feedback)

    # Run the Swarm
    result = swarm(
        task,
        invocation_state=build_invocation_state(project_id, phase)
    )

    # Handle interrupts in a loop
    while result.stop_reason == "interrupt":
        for interrupt in result.interrupts:
            # Surface question to customer via WebSocket
            publish_interrupt_to_dashboard(project_id, interrupt)
            # Block until customer responds
            response = wait_for_interrupt_response(project_id, interrupt.id)
            interrupt.response = response

        # Resume Swarm with responses
        result = swarm(result.interrupt_responses)

    # Report result to Step Functions
    sfn_client.send_task_success(
        taskToken=task_token,
        output=json.dumps({
            "project_id": project_id,
            "phase": phase,
            "status": str(result.status),
            "deliverables": extract_deliverables(result),
            "summary": extract_summary(result),
        })
    )
```

#### 4.3 Approval API

API Gateway endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /projects` | POST | Create new project (upload SOW, start Step Functions) |
| `GET /projects/{id}/status` | GET | Current phase, pending approvals |
| `GET /projects/{id}/deliverables` | GET | List deliverables by phase |
| `POST /projects/{id}/approve` | POST | Customer approves (calls `SendTaskSuccess`) |
| `POST /projects/{id}/revise` | POST | Customer requests changes (calls `SendTaskFailure` with feedback) |
| `POST /projects/{id}/message` | POST | Customer sends message to PM agent (standalone Lambda PM) |
| `POST /projects/{id}/interrupt/{interruptId}/respond` | POST | Customer responds to agent clarification question |

#### 4.4 Phase Transition Protocol

Implement the summarization step (runs inside the PM Review Lambda):

1. PM reads all deliverables and agent outputs from the Swarm
2. PM validates deliverables against SOW acceptance criteria
3. PM updates the task ledger with: decisions made, deliverables produced, open items
4. STM for the phase is summarized into LTM (raw conversation pruned)
5. Durable decisions committed to Git as ADRs
6. Knowledge Base re-syncs from Git/S3 to index new artifacts

#### 4.5 Remaining Agents

Implement Dev, Data, QA agents with their tools.

#### 4.6 All Phase Swarms

Wire up all 5 phase Swarms with the correct agent subsets:

| Phase | Entry Agent | Swarm Agents | Swarm Size Config |
|-------|-------------|-------------|-------------------|
| Discovery | PM | PM, SA | 2-agent (max_handoffs=10) |
| Architecture | SA | SA, Infra, Security | 3-agent (max_handoffs=15) |
| POC | Dev | Dev, Infra, Data, Security, SA | 5-agent (max_handoffs=15) |
| Production | Dev | Dev, Infra, Data, Security, QA | 5-agent (max_handoffs=15) |
| Handoff | PM | PM, SA | 2-agent (max_handoffs=10) |

Each Swarm invocation is followed by a PM Review step (Lambda) before the approval gate.

**Test:**

- Start a full project by invoking Step Functions with a sample SOW (use `POST /projects` API)
- Verify Discovery phase runs, produces deliverables, enters approval gate
- Approve via API, verify Architecture phase starts
- Request revision, verify Discovery re-runs with feedback
- Run through all 5 phases with approvals
- Verify task ledger tracks the full project lifecycle

---

### Milestone 5: Customer Dashboard

**Goal:** Customer-facing SPA for interacting with the system.

**Build:**

#### 5.1 React Project Setup

Vite + React + Shadcn/ui + TanStack Query

#### 5.2 Authentication

Cognito user pool + hosted UI for customer login

#### 5.3 Project Kickoff Flow

- "New Project" page with SOW upload form (PDF, DOCX, text)
- Upload SOW to S3, call `POST /projects` to create DynamoDB record and start Step Functions
- Redirect to project dashboard after creation

#### 5.4 Chat View

- WebSocket connection to API Gateway for real-time streaming
- During PM phases: messages go to PM agent in the running Swarm
- During other phases/approval gates: messages go to a **standalone PM Lambda** that reads the task ledger and Git artifacts to answer questions
- Uses Strands `stream_async` for streaming agent responses
- Message history persisted in AgentCore Memory

#### 5.5 Kanban Board

- Reads from DynamoDB task ledger via API
- Cards show phase, status, agents, deliverables
- Approve/Revise actions trigger Step Functions API calls
- Real-time updates via WebSocket

#### 5.6 Artifact Browser

- Lists files from Git repo via API
- Inline rendering for markdown, code highlighting
- Download for binary files
- Git history per file

#### 5.7 Notifications

- Pending approval notifications
- Phase completion notifications
- Agent question notifications (Strands interrupts)

**Test:**

- End-to-end: Customer logs in → starts project with SOW → views Discovery progress → approves deliverables → tracks through all phases
- Chat with PM agent, ask technical questions that get delegated to specialists
- Download architecture docs and review code artifacts

---

### Milestone 6: Self-Improvement System

**Goal:** CloudCrew gets better with every engagement through cross-engagement learning.

**Build:**

#### 6.1 Metrics Hook + DynamoDB Table

Create the `cloudcrew-metrics` DynamoDB table (PAY_PER_REQUEST). Implement the `metrics_hook` as a Strands HookProvider that tracks token usage, agent turns, and handoff events per invocation. The hook writes to working memory during the Swarm. Update the PM Review Lambda to aggregate phase-level metrics.

**Schema:**
- `ENGAGEMENT#{project_id}` / `SUMMARY` — per-engagement totals
- `ENGAGEMENT#{project_id}` / `PHASE#{name}` — per-phase breakdowns with per-agent cost
- `TIMELINE` / `#{timestamp}#{project_id}` — cross-engagement timeline
- `ENGAGEMENT#{project_id}` / `SURVEY` — post-engagement survey

**Test:**
- Unit test the metrics hook with mock Bedrock calls
- Verify token counts accumulate correctly in working memory
- Verify PM Review Lambda writes phase-level metrics

#### 6.2 Structured Customer Feedback + Survey

Update the approval gate API to accept structured ratings (quality, relevance, completeness: 1-5) alongside the approve/revise decision. Update the task ledger `customer_feedback` field to include ratings. Add a post-engagement survey endpoint and dashboard page.

**Test:**
- Approval API accepts and stores structured feedback
- Survey API stores results in metrics table
- Dashboard renders rating inputs at approval gates

#### 6.3 Pattern Library (S3 + KB + Tools)

Create the `cloudcrew-patterns` S3 bucket. Create a dedicated Bedrock KB data source pointing to it. Implement pattern library tools:
- `search_patterns(query, category?, tags?)` — searches pattern KB
- `use_pattern(pattern_id)` — copies pattern into project, increments `times_used` in metadata.json
- `contribute_pattern(artifact_path, category, tags)` — creates draft pattern from engagement artifact
- `promote_pattern(pattern_id)` — QA-only, promotes candidate → proven if 3+ uses and >80% success rate

Add pattern library search instructions to all agent system prompts.

**Test:**
- Seed the pattern library with 2-3 sample patterns
- Verify `search_patterns` returns relevant results
- Verify `use_pattern` copies files and updates metadata
- Verify `contribute_pattern` creates draft with correct metadata
- Verify `promote_pattern` enforces tier criteria

#### 6.4 Retrospective Phase (Step Functions + Swarm)

Add the Retrospective phase to the Step Functions state machine after Handoff:
- Retrospective Swarm (PM, QA) — no customer approval gate
- Finalize Metrics Lambda — aggregates metrics, writes timeline item, triggers KB re-sync
- Post-engagement survey trigger

PM responsibilities: compare outcomes vs. SOW, write lessons to cross-engagement LTM, identify artifacts for pattern library. QA responsibilities: score deliverable quality, evaluate and promote pattern candidates.

**Test:**
- Verify Retrospective runs automatically after Handoff approval
- Verify PM writes lessons to LTM and contributes patterns
- Verify QA promotes qualifying patterns
- Verify Finalize Metrics Lambda writes SUMMARY and TIMELINE items
- Verify KB re-syncs with newly contributed patterns

#### 6.5 Cross-Engagement Analytics

Build tools/queries for analyzing trends across engagements:
- Cost trends over time (are engagements getting cheaper?)
- Satisfaction trends (are customers happier?)
- Pattern library growth and usage statistics
- Agent cost optimization recommendations

This is primarily a reporting/query layer on top of the metrics table — no new infrastructure.

**Test:**
- Query TIMELINE items and verify trend calculations
- Verify pattern library statistics (total patterns by tier, usage counts)
- Run 2+ test engagements and verify cross-engagement queries return meaningful data

---

## Testing Strategy

### Unit Tests

- Each tool independently (mock external services)
- Agent configuration validation (correct tools, model, prompts)
- Task ledger CRUD operations
- SOW parser with sample documents
- Pydantic model validation

### Integration Tests

- Single agent with real Bedrock calls (use small test tasks)
- Two-agent Swarm with handoffs
- Step Functions state machine transitions
- API Gateway → Lambda → Swarm pipeline
- Memory persistence across invocations
- Knowledge Base search accuracy

### End-to-End Tests

- Full project lifecycle with a sample SOW
- Run through all 5 delivery phases + retrospective with mock approvals
- Verify all deliverables are produced
- Verify task ledger is complete and accurate
- Verify engagement metrics are written and cross-engagement queries work
- Verify pattern library contributions and promotions after multiple engagements

### Performance Benchmarks

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Swarm execution time per phase | < 20 min | `result.execution_time` |
| Token usage per phase | Track for cost projections | `result.accumulated_usage` |
| Context growth per handoff | Identify summarization triggers | Log context size at each handoff |
| Handoff count per phase | < 15 (within safety limits) | `result.execution_order` length |
| Approval gate round-trip | < 1s (API latency) | API Gateway metrics |

---

## Configuration

### Environment Variables

```bash
# Bedrock
BEDROCK_REGION=us-east-1

# DynamoDB
TASK_LEDGER_TABLE=cloudcrew-projects
METRICS_TABLE=cloudcrew-metrics

# AgentCore Memory
STM_MEMORY_ID=mem-xxx
LTM_MEMORY_ID=mem-yyy

# Knowledge Base
KNOWLEDGE_BASE_ID=kb-zzz
PATTERNS_KNOWLEDGE_BASE_ID=kb-patterns

# Pattern Library
PATTERNS_BUCKET=cloudcrew-patterns

# Git
PROJECT_REPO_URL=https://github.com/org/cloudcrew-project-{customer}

# Step Functions
STATE_MACHINE_ARN=arn:aws:states:us-east-1:123456789:stateMachine:cloudcrew

# Dashboard
API_GATEWAY_URL=https://api.cloudcrew.example.com
WEBSOCKET_URL=wss://ws.cloudcrew.example.com
```

### Model Configuration

During testing (single Bedrock API key):

```python
# All agents share the same AWS credentials
# Just different model IDs
OPUS = BedrockModel(model_id="us.anthropic.claude-opus-4-6-v1")
SONNET = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514")
```

Production (per-agent budgets):

```python
from strands.agent.hooks import HookProvider, HookRegistry
from strands.types.event import AfterModelCallEvent

class TokenBudgetHook(HookProvider):
    def __init__(self, agent_name: str, budget: int):
        self.agent_name = agent_name
        self.budget = budget
        self.consumed = 0

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(AfterModelCallEvent, self.track_usage)

    def track_usage(self, event: AfterModelCallEvent) -> None:
        self.consumed += event.usage.get("total_tokens", 0)
        if self.consumed > self.budget:
            logger.warning(
                f"{self.agent_name} exceeded token budget: "
                f"{self.consumed}/{self.budget}"
            )
```

---

## Deployment

### Prerequisites

1. **AWS CLI** configured with credentials for your AWS account
2. **Terraform** >= 1.7.0 installed
3. **Docker** installed (for building phase runner image)

### One-Time Bootstrap

Creates the S3 bucket and DynamoDB table for Terraform remote state. These cost pennies per month and stay running permanently.

```bash
make bootstrap-init
make bootstrap-apply
```

After bootstrap completes, the output values match what's hardcoded in `infra/terraform/backend.tf`. If you used custom variable overrides (different bucket name), update `backend.tf` to match.

### Terraform Variables

Create `infra/terraform/terraform.tfvars` (gitignored — never committed):

```hcl
aws_region            = "us-east-1"
environment           = "dev"
budget_alert_email    = "your-email@example.com"
monthly_budget_amount = 50
```

See `infra/terraform/example.tfvars` for the template.

### Per-Milestone Deploy/Test/Destroy Cycle

```bash
# 1. Initialize (first time, or after destroy)
make tf-init

# 2. Review what will be created
make tf-plan

# 3. Deploy (interactive confirmation)
make tf-apply

# 4. If milestone requires Docker image:
make docker-build
make docker-push

# 5. Run your tests against the live infrastructure

# 6. Tear down when done testing
make tf-destroy
```

**Always destroy after testing.** The only resources that persist between sessions are the bootstrap resources (state bucket + lock table).

### Cost per Milestone

| Milestone | Resources | Estimated Cost While Running |
|-----------|-----------|------------------------------|
| 1 (Single Agent) | DynamoDB, S3 | ~$1/month |
| 2 (Two-Agent Swarm) | + ECR | ~$1/month |
| 3 (Task Ledger + Memory) | + DynamoDB config | ~$1/month |
| 4 (Step Functions + ECS) | + VPC, ECS, Step Functions, Lambda, API GW, Cognito | ~$5-15/month |
| 5 (Dashboard) | + CloudFront, S3 hosting | ~$5-15/month |
| 6 (Self-Improvement) | + DynamoDB metrics table, S3 patterns bucket, Bedrock KB data source | ~$5-15/month |

All costs assume resources are destroyed after testing. Bedrock token costs are separate.

### CI Validation

The `quality.yml` CI pipeline validates Terraform on every PR:
- `terraform fmt -check` — formatting
- `terraform validate` — HCL syntax and references
- Checkov scan — security and best practices

CI never runs `plan` or `apply`. All deployment is manual via Makefile targets.

---

## Development Workflow

1. **Branch strategy:** Trunk-based. `main` is the production branch. All changes go through short-lived feature branches and pull requests.
2. **PR review:** All PRs require passing CI (lint, typecheck, test, security, terraform-validate).
3. **Testing cadence:** Run unit tests on every push. Run integration tests before merge. Run e2e tests before release.
4. **Agent prompt iteration:** System prompts live in version-controlled files (`src/agents/prompts/`). Changes to prompts are PRs with test results showing improvement.

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Swarm context window exhaustion | Monitor context growth per handoff; implement mid-Swarm summarization if needed |
| Agent produces incorrect artifacts | Pairwise review (SA→code, Security→IaC, QA→app code) + PM Review step catches issues before customer sees them |
| Customer approval takes too long | Step Functions `waitForTaskToken` handles unlimited wait; dashboard shows pending items |
| Token costs exceed budget | Per-agent token tracking hooks; Sonnet for mechanical work, Opus only for reasoning |
| Agent fails mid-Swarm | Step Functions retry with error context; Swarm re-invoked from phase start. Git artifacts from partial run are preserved. |
| Agents disagree on approach | SA has architectural authority; PM is tiebreaker; hierarchy resolves conflicts |
| Swarm scale limits unknown | Start conservative (max_handoffs=15 for 3+ agents, 10 for 2 agents); measure and tune per phase |
| Within-phase interrupt unanswered | ECS task blocks indefinitely; sends reminder after 30 min; no auto-cancel |
| Knowledge Base stale within phase | Agents use `git_read` for same-phase artifacts; KB only re-syncs at phase transitions |
| ECS task crash | Step Functions retries 1x automatically; task ledger + Git preserve partial progress |
| DynamoDB item size limit (400KB) | Task ledger stores metadata only (not artifact content). Unlikely to exceed limit for structured fields. Monitor. |
| Git merge conflicts between agents | Swarm agents execute sequentially (one at a time). Scoped write tools enforce directory boundaries. Pull-before-write in git tools prevents conflicts. |
