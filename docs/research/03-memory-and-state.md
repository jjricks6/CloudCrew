# Memory and State Management Research

Research conducted: 2026-02-16

## Layered Memory Model for CloudCrew

Multi-agent systems need multiple layers of memory operating at different scopes and timescales.

| Layer | Scope | Technology | Purpose |
|-------|-------|------------|---------|
| **Working Memory** | Within a single agent invocation | Strands `invocation_state` + pattern-specific context | Agents coordinate within a phase |
| **Short-term Memory (STM)** | Within a session | AgentCore Memory (STM) | Persist agent conversations within a work session |
| **Long-term Memory (LTM)** | Across sessions | AgentCore Memory with strategies | Remember architecture decisions, customer preferences, lessons learned |
| **Project Knowledge Base** | Entire project lifetime | Git repo + Bedrock Knowledge Base | Agents read/write to project repo; KB indexes for semantic search |
| **Task/State Store** | Entire project lifetime | DynamoDB or Step Functions | Track phases, approvals, task assignments |

---

## Amazon Bedrock AgentCore Memory

### Overview

Managed memory service for AI agents. Provides both short-term and long-term memory with intelligent extraction.

### Short-Term Memory (STM)

Stores raw conversation turns within a session. No intelligent extraction.

```python
from bedrock_agentcore.memory import MemoryClient

client = MemoryClient(region_name='us-west-2')
stm = client.create_memory_and_wait(
    name="CloudCrew_STM",
    strategies=[],  # Empty = no extraction
    event_expiry_days=7
)
```

**Capabilities:**
- Store exact conversation messages
- Retrieve last K turns
- Session-scoped
- Instant retrieval (no processing)

### Long-Term Memory (LTM)

Intelligently extracts and retains information across sessions using strategies.

```python
ltm = client.create_memory_and_wait(
    name="CloudCrew_LTM",
    strategies=[
        {"userPreferenceMemoryStrategy": {
            "name": "prefs",
            "namespaces": ["/user/preferences/"]
        }},
        {"semanticMemoryStrategy": {
            "name": "facts",
            "namespaces": ["/user/facts/"]
        }},
        {"summaryMemoryStrategy": {
            "name": "summaries",
            "namespaces": ["/summaries/{actorId}/{sessionId}"]
        }}
    ],
    event_expiry_days=30
)
```

**Three built-in strategies:**

| Strategy | Purpose | Namespace pattern |
|----------|---------|-------------------|
| `summaryMemoryStrategy` | Summarizes conversation sessions | `/summaries/{actorId}/{sessionId}` |
| `userPreferenceMemoryStrategy` | Extracts user preferences | `/preferences/{actorId}` |
| `semanticMemoryStrategy` | Extracts factual information | `/facts/{actorId}` |

**Extraction is async** — takes 5-10 seconds after messages are written.

### Strands Integration

AgentCore Memory has a direct Strands session manager integration:

```python
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from strands import Agent

config = AgentCoreMemoryConfig(
    memory_id="mem-xxx",
    session_id="session-123",
    actor_id="pm-agent",
    retrieval_config={
        "/preferences/{actorId}": RetrievalConfig(top_k=5, relevance_score=0.7),
        "/facts/{actorId}": RetrievalConfig(top_k=10, relevance_score=0.3),
    }
)

with AgentCoreMemorySessionManager(config, region_name="us-east-1") as session_manager:
    agent = Agent(
        system_prompt="You are a helpful assistant.",
        session_manager=session_manager,
    )
    agent("What does the customer need?")
```

**Config parameters:**

| Parameter | Description |
|-----------|-------------|
| `memory_id` | Memory resource ID |
| `session_id` | Session identifier |
| `actor_id` | User/actor identifier |
| `retrieval_config` | Dict of namespace → RetrievalConfig |
| `batch_size` | Messages to buffer before sending (1-100) |

**Important:** Only one agent per session supported currently.

### Alternative: Hook-based Memory Integration

Instead of session manager, you can use hooks for more control:

```python
from strands.hooks import AgentInitializedEvent, MessageAddedEvent, HookProvider

class MemoryHook(HookProvider):
    def on_agent_initialized(self, event):
        # Load previous conversation turns
        turns = memory_client.get_last_k_turns(
            memory_id=MEMORY_ID,
            actor_id="user",
            session_id=event.agent.state.get("session_id"),
            k=3
        )
        if turns:
            context = "\n".join([f"{m['role']}: {m['content']['text']}"
                               for t in turns for m in t])
            event.agent.system_prompt += f"\n\nPrevious:\n{context}"

    def on_message_added(self, event):
        # Save message to memory
        msg = event.agent.messages[-1]
        memory_client.create_event(
            memory_id=MEMORY_ID,
            actor_id="user",
            session_id=event.agent.state.get("session_id"),
            messages=[(str(msg["content"]), msg["role"])]
        )
```

### Semantic Search on Memory

```python
session.search_long_term_memories(
    query="customer's architecture preferences",
    namespace_prefix="/",
    top_k=3
)
```

---

## Git as Shared Workspace

The project's Git repository serves as the primary artifact store and shared workspace for all agents.

### Structure

```
cloudcrew-project-{customer}/
├── docs/
│   ├── architecture/          # SA agent writes here
│   │   ├── decisions/         # ADRs
│   │   ├── diagrams/          # Architecture diagrams
│   │   └── design.md
│   ├── project-plan.md        # PM agent writes here
│   └── runbooks/              # Ops docs
├── infra/
│   ├── terraform/             # Infra agent writes here
│   └── ci-cd/
├── app/
│   ├── src/                   # Dev agent writes here
│   └── tests/                 # QA agent writes here
├── data/
│   └── pipelines/             # Data agent writes here
└── security/
    └── scan-results/          # Security agent writes here
```

### Agent Git interaction

Each agent gets Git tools scoped to its domain:
- SA agent: read/write `docs/architecture/`
- Infra agent: read/write `infra/`
- Dev agent: read/write `app/`
- All agents: read everything (for context)

---

## DynamoDB for Task/State Tracking

For tracking project phases, approval states, and task assignments.

### Potential table design

```
PK: PROJECT#{project_id}
SK: PHASE#{phase_name}

Attributes:
- status: PENDING | IN_PROGRESS | AWAITING_APPROVAL | APPROVED | COMPLETED
- assigned_agents: [list of agent names]
- started_at: timestamp
- completed_at: timestamp
- approval_requested_at: timestamp
- approved_by: customer_id
- deliverables: [list of artifact paths in git]
- customer_feedback: text
```

### Approval gate flow

1. Phase completes → Swarm/Graph node finishes
2. AfterNodeCallEvent hook fires → writes approval request to DynamoDB
3. Customer-facing API checks DynamoDB for pending approvals
4. Customer reviews deliverables (in Git) and approves/requests changes
5. Approval written to DynamoDB → triggers next phase (via EventBridge or polling)

---

## Amazon Bedrock Knowledge Bases

For semantic search over project artifacts.

### Use case

As agents produce documents and code, index them in a Knowledge Base so any agent can search for relevant context:
- "What architecture decisions have been made about the data layer?"
- "What did the customer say about authentication requirements?"
- "What Terraform modules have already been written?"

### Data source

S3 bucket synced from the Git repo. Knowledge Base indexes documents, code, and conversation logs.

---

## AWS Step Functions as Orchestration Alternative

Step Functions could manage the top-level phase orchestration:

**Strengths:**
- Exactly-once execution guarantee
- Visual workflow debugging
- `.waitForTaskToken` for HITL approval gates (built-in!)
- Built-in retry/error handling
- Up to 1 year runtime

**How it could work:**
- Step Functions manages the phase graph: Discovery → Architecture → POC → Production → Handoff
- Each phase step invokes a Lambda/ECS task running a Strands Swarm
- `.waitForTaskToken` pauses between phases until customer approves
- State passed between steps via JSON

**Trade-off:** Adds infrastructure complexity but gives you native HITL approval gates without custom building.

---

## Memory Architecture Recommendation for CloudCrew

### Per-agent memory

Each agent has its own AgentCore Memory session with:
- STM for its conversation within the current phase
- LTM with semantic strategy for extracting important facts/decisions

### Shared project memory

A separate AgentCore Memory resource shared across all agents:
- Customer requirements and feedback
- Architecture decisions
- Cross-agent coordination notes

### Project knowledge base

Bedrock Knowledge Base indexing the Git repo for semantic search across all project artifacts.

### Approval state

DynamoDB table tracking phase status and approval gates. EventBridge or polling for phase transitions.

### Key design principle

Agents should be able to:
1. **Remember their own work** (per-agent STM/LTM)
2. **Know what other agents decided** (shared memory + Git repo)
3. **Search project artifacts** (Knowledge Base)
4. **Know the project status** (DynamoDB state store)

---

## Additional Research: Deep Dive Topics

### Private vs Shared Memory — Metadata-Based Filtering

Rather than maintaining separate stores for each agent, use **metadata-based filtering on shared stores**:

| Layer | Private Memory | Shared Memory |
|-------|---------------|---------------|
| Working State | DynamoDB: agent-specific partition key (`project#agentId`) | DynamoDB: project-level partition key (`project#shared`) |
| Semantic Memory | Agent-specific namespace in AgentCore Memory (filtered by `agent_id`) | Shared namespace queryable by all agents |
| Knowledge | N/A | Bedrock Knowledge Base synced from project docs |
| Conversation History | Each agent maintains its own session | Supervisor agent captures cross-agent orchestration history |
| Code/Artifacts | Agent-specific Git branches for WIP | Merged code on main branch |

A single AgentCore Memory resource with namespace-based scoping (e.g., `/private/{agentId}/` and `/shared/`) gives both private and shared views without data duplication.

### DynamoDB Schema for Agent State

```
Table: cloudcrew-projects

PK: PROJECT#{project_id}#AGENT#{agent_id}
SK: SESSION#{session_id}#TS#{timestamp}
Attributes:
  - conversation_history (JSON)
  - agent_state (JSON)
  - phase (string)
  - status (string)
  - ttl (number, for auto-cleanup)

GSI1: PK=PROJECT#{project_id}, SK=timestamp
  → Query all agent activity across a project

GSI2: PK=AGENT#{agent_id}, SK=status
  → Query all sessions for a specific agent by status
```

**Why DynamoDB for this:**
- Single-digit millisecond latency
- Scales to any number of concurrent agents/sessions
- TTL for automatic cleanup of old sessions
- On-demand pricing (zero cost when agents idle)
- Item-level transactions for safe concurrent updates

**Limitation:** 400 KB item size limit — conversation histories can exceed this. Use S3 for overflow and store a reference in DynamoDB.

### Tiered Persistence Strategy

Projects span weeks or months. Different data has different lifetimes:

**Tier 1 — Durable Project Record (months-years)**
- Git repository: code, ADRs, structured agent metadata files
- S3: project documents, meeting transcripts, design mockups
- Bedrock Knowledge Base: synced from Git + S3 for semantic retrieval
- These survive indefinitely and form the canonical project record

**Tier 2 — Structured State (weeks-months)**
- DynamoDB: current project phase, agent assignments, task status
- AgentCore Memory (event memory): chronological log of significant agent actions
- Actively queried during project, archived after completion

**Tier 3 — Working Memory (hours-days)**
- Agent session memory: current conversation context within a task
- AgentCore Memory (semantic memory): recent observations, current blockers
- Ephemeral — summarized/pruned on a rolling basis

### Phase Transition Protocol

When moving between phases (e.g., "Architecture" → "POC"):

1. Each agent **summarizes its phase work** and writes to shared memory
2. A coordinator agent **consolidates phase summaries** into the project knowledge base
3. Old working memory is **pruned**; durable decisions are **persisted to Git/S3**
4. Next-phase agents **load context** from shared memory + Knowledge Base

This prevents unbounded context growth while preserving important decisions.

### Architecture Decision Records (ADRs) in Git

Agents write ADRs as structured markdown:

```
docs/decisions/
  ADR-001-database-choice.md
  ADR-002-auth-strategy.md
  ADR-003-api-versioning.md
```

These are committed to Git, synced to S3, and ingested into the Knowledge Base. Any agent can then query: "What database did we choose and why?"

### Knowledge Curation

Over time, agents accumulate observations that don't warrant formal ADRs: "The customer prefers minimalist UI", "The API rate limit is 100 req/s", "The test suite takes 8 minutes to run."

Options for managing this:
- A **knowledge curator** agent (or scheduled job) periodically reviews accumulated memories
- Promotes important ones to ADRs
- Prunes stale entries
- Prevents the knowledge base from becoming noisy over time

### Memory Technology Comparison Matrix

| Criterion | AgentCore Memory | Bedrock KBs | DynamoDB | Git | EventBridge/SQS |
|-----------|-----------------|-------------|----------|-----|-----------------|
| **Best for** | Semantic + event memory | Static doc retrieval (RAG) | Structured state | Code artifacts, durable decisions | Real-time agent comms |
| **Multi-agent sharing** | Native | Native (read-only) | Native (key design) | Native (branches) | Native |
| **Semantic search** | Yes | Yes | No | No | No |
| **Real-time updates** | Yes | No (batch sync) | Yes (ms latency) | No (push/pull) | Yes |
| **Persistence** | Configurable | Indefinite | Indefinite (TTL option) | Indefinite | Transient |
| **Write-back from agents** | Yes (API) | No (write to S3, re-sync) | Yes (API) | Yes (git commit) | Yes (publish) |
| **Audit trail** | Event log | Sync history | DynamoDB Streams | Full git history | CloudWatch logs |

### Practical Concerns

1. **Context window growth**: In Swarm mode after many handoffs across 5-7 agents, accumulated conversation history can exceed model context limits. Need summarization or truncation strategies.

2. **Cost**: Each agent invocation uses LLM tokens. Use smaller models for simpler agents (Haiku for classification, Sonnet for generation). A full project lifecycle could consume millions of tokens.

3. **Shared state race conditions**: With parallel execution in Graph, two agents writing to same state keys can conflict. Define clear ownership of state keys per agent.

4. **Memory conflict resolution**: AgentCore Memory has no built-in conflict resolution. If two agents write conflicting info simultaneously, last write wins. Design namespaces to minimize overlap.
