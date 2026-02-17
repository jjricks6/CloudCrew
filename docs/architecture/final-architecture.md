# CloudCrew Architecture

> Definitive architecture reference for the CloudCrew multi-agent AI system.
> Last updated: 2026-02-17

---

## 1. Overview

CloudCrew is a multi-agent AI system where 7 specialized agents collaborate to deliver real software projects. Given a Statement of Work (SOW), agents autonomously coordinate through phased delivery — producing architecture documents, ADRs, POCs, production code, IaC, CI/CD pipelines, security reviews, and test suites. A customer reviews and approves deliverables at phase gates.

---

## 2. System Architecture

### High-Level Design

Two-tier orchestration:

- **Tier 1 — Phase Orchestration:** AWS Step Functions manages the project lifecycle as a state machine. Phases execute sequentially with durable approval gates between each phase using `waitForTaskToken`. This handles the "hours/days" timescale — customers may take time to review.
- **Tier 2 — Within-Phase Collaboration:** Strands Agents Swarm enables emergent collaboration between agents within each phase. Agents hand off work, review each other's outputs, and self-organize. Strands native interrupts handle "minutes" timescale HITL (clarifying questions mid-phase).

### Phase Flow (Step Functions State Machine)

```
┌─────────────┐
│  Start       │
└──────┬──────┘
       ▼
┌─────────────────────────────────────┐
│  Discovery Phase (ECS)               │
│  Swarm: PM, SA                       │
│  Deliverables: Project plan,         │
│    requirements, initial architecture│
└──────┬──────────────────────────────┘
       ▼
┌─────────────────────────────────────┐
│  PM Review (Lambda)                  │
│  Validate deliverables against SOW   │
│  Update task ledger, compile package │
└──────┬──────────────────────────────┘
       ▼
┌─────────────────────────────────────┐
│  Approval Gate (waitForTaskToken)   │
│  Customer reviews deliverables       │
│  ├── Approved → next phase          │
│  └── Revision → re-run Discovery    │
│       with customer feedback         │
└──────┬──────────────────────────────┘
       ▼
┌─────────────────────────────────────┐
│  Architecture Phase (ECS)            │
│  Swarm: SA, Infra, Security          │
│  Deliverables: Architecture diagrams,│
│    ADRs, cost estimates, security    │
│    review                            │
└──────┬──────────────────────────────┘
       ▼
┌─────────────────────────────────────┐
│  PM Review → Approval Gate           │
└──────┬──────────────────────────────┘
       ▼
┌─────────────────────────────────────┐
│  POC Phase (ECS)                     │
│  Swarm: Dev, Infra, Data, Security,  │
│    SA                                │
│  Deliverables: Working POC, findings │
│    doc, security-reviewed IaC        │
└──────┬──────────────────────────────┘
       ▼
┌─────────────────────────────────────┐
│  PM Review → Approval Gate           │
└──────┬──────────────────────────────┘
       ▼
┌─────────────────────────────────────┐
│  Production Phase (ECS)              │
│  Swarm: Dev, Infra, Data, Security,  │
│    QA                                │
│  Deliverables: Production code, IaC, │
│    CI/CD, tests, security scans      │
└──────┬──────────────────────────────┘
       ▼
┌─────────────────────────────────────┐
│  PM Review → Approval Gate           │
└──────┬──────────────────────────────┘
       ▼
┌─────────────────────────────────────┐
│  Handoff Phase (ECS)                 │
│  Swarm: PM, SA                       │
│  Deliverables: Documentation,        │
│    runbooks, knowledge transfer      │
└──────┬──────────────────────────────┘
       ▼
┌─────────────────────────────────────┐
│  PM Review → Approval Gate           │
└──────┬──────────────────────────────┘
       ▼
┌─────────────────────────────────────┐
│  Retrospective Phase (ECS)           │
│  Swarm: PM, QA                       │
│  Internal: metrics, lessons learned, │
│    pattern library contributions     │
│  (No customer approval gate)         │
└──────┬──────────────────────────────┘
       ▼
┌─────────────────────────────────────┐
│  Finalize Metrics (Lambda)           │
│  Aggregate metrics, sync patterns KB │
└──────┬──────────────────────────────┘
       ▼
┌─────────────────────────────────────┐
│  Post-Engagement Survey              │
│  Customer rates overall experience   │
└──────┬──────────────────────────────┘
       ▼
┌─────────────┐
│  Complete    │
└─────────────┘
```

Each phase invocation is an **ECS Fargate task** running a Strands Swarm. ECS is required (not Lambda) because Swarm execution can exceed Lambda's 15-minute timeout and because within-phase interrupts require the process to remain alive while waiting for customer responses. Step Functions passes JSON state (project_id, phase context, customer feedback from previous approval) between states.

### PM Review Step

After every phase Swarm completes, a **PM Review step** runs before the approval gate. This is a separate **Lambda invocation** where the PM agent:

1. Reads all deliverables produced during the phase (via `git_read`)
2. Reads the task ledger for decisions and open items
3. Validates deliverables against SOW acceptance criteria
4. Updates the task ledger with the phase summary
5. Compiles the customer-facing deliverable package

This ensures the PM reviews every phase's output even though it's not in every Swarm. The Step Functions flow is actually: `Phase Swarm → PM Review → Approval Gate`.

### Within-Phase Coordination (Strands Swarm)

Each phase runs a Swarm with the agents specified for that phase. Swarm configuration varies by phase size:

**Phases with 3+ agents** (Architecture, POC, Production):

| Parameter | Value | Notes |
|-----------|-------|-------|
| `max_handoffs` | 15 | Conservative; tune based on testing |
| `max_iterations` | 15 | Matches max_handoffs |
| `execution_timeout` | 1200s (20m) | Total phase time budget |
| `node_timeout` | 300s (5m) | Per-agent turn limit |
| `repetitive_handoff_detection_window` | 8 | Detects ping-pong patterns |
| `repetitive_handoff_min_unique_agents` | 3 | Requires diversity in handoffs |

**Phases with 2 agents** (Discovery, Handoff):

| Parameter | Value | Notes |
|-----------|-------|-------|
| `max_handoffs` | 10 | Fewer agents = fewer handoffs needed |
| `max_iterations` | 10 | Matches max_handoffs |
| `execution_timeout` | 900s (15m) | Smaller scope |
| `node_timeout` | 300s (5m) | Per-agent turn limit |
| `repetitive_handoff_detection_window` | 6 | Shorter window for 2-agent detection |
| `repetitive_handoff_min_unique_agents` | 2 | Only 2 agents available |

Within a Swarm:

- Entry agent receives the task + context from Step Functions
- Agents hand off using `handoff_to_agent()` with explicit messages
- Review patterns are encoded in system prompts (SA reviews arch-impacting code, Security reviews all IaC, QA reviews all app code)
- If an agent needs customer input, it uses Strands `event.interrupt()` — the Swarm pauses, the ECS task surfaces the question to the customer dashboard via WebSocket, then blocks waiting for the response. When the customer responds (via API), the ECS task resumes the Swarm with `InterruptResponseContent`. Since ECS has no timeout ceiling, this can wait as long as needed (though practically a within-phase question should resolve in minutes).
- Each agent writes artifacts to the Git repo using scoped Git tools. Agents must **pull before writing** to avoid conflicts with artifacts written by previous agents in the same phase.
- Within a phase, agents access each other's artifacts via `git_read` (not Knowledge Base search — the KB only re-syncs at phase transitions)

---

## 3. HITL Model — Two Timescales

| Timescale | Mechanism | Use Case |
|-----------|-----------|----------|
| Minutes (within-phase) | Strands `event.interrupt()` | Agent needs clarification: "Should we use Cognito or Auth0?" |
| Hours/Days (between-phase) | Step Functions `waitForTaskToken` | Customer reviews phase deliverables, approves or requests changes |

### Between-Phase Flow

1. Swarm completes → returns result to Step Functions
2. Step Functions enters `waitForTaskToken` state, stores task token in DynamoDB
3. Customer dashboard shows pending approval with deliverable links
4. Customer reviews artifacts in Git, clicks Approve / Request Changes
5. Dashboard API calls `SendTaskSuccess` (approved) or `SendTaskFailure` (revision requested) with the stored task token
6. Step Functions resumes — either moves to next phase or re-runs current phase with feedback

### Within-Phase Flow

1. Agent raises `event.interrupt("clarification", reason="Should we use Cognito or Auth0?")`
2. Swarm pauses, returns interrupt to Lambda/ECS task
3. Lambda publishes question to customer dashboard via WebSocket
4. Customer responds
5. Lambda resumes Swarm with `InterruptResponseContent`
6. Agent receives response and continues

---

## 4. Agent Roster

7 agents, each with scoped tools, specific models, and review responsibilities.

| Agent | Model | Primary Phases | Scoped Tools | Reviews |
|-------|-------|----------------|--------------|---------|
| **PM** | Opus 4.6 | Discovery, Handoff (all phases advisory) | SOW parser, task ledger (DynamoDB), customer comms, Git (project-plan) | Deliverables against SOW acceptance criteria |
| **SA** | Opus 4.6 | Discovery, Architecture, Handoff | Diagram generator, AWS docs, ADR writer, cost estimator, Git (docs/architecture), KB search | Architecture-impacting code changes |
| **Infra** | Sonnet | Architecture (advisory), POC, Production | Terraform gen/validate, Checkov, AWS provider docs, Git (infra/) | CI/CD configurations |
| **Dev** | Sonnet | POC, Production | Code gen/edit, test runner, linter, Git (app/), package managers | N/A (receives reviews) |
| **Data** | Sonnet | POC, Production | Schema design, SQL/NoSQL tools, pipeline generator, Git (data/) | Data migration scripts |
| **Security** | Opus 4.6 | Architecture (advisory), POC, Production | Checkov/tfsec, OWASP scanner, IAM analyzer, Git (security/) | ALL IaC and IAM policies |
| **QA** | Sonnet | Production | Test frameworks, integration runner, load testing, Git (app/tests/) | ALL application code for testability |

**Model rationale:**

- **Opus 4.6** for agents requiring deep reasoning: PM (SOW decomposition, cross-domain synthesis), SA (architecture trade-offs), Security (attack surface analysis)
- **Sonnet** for agents doing more mechanical/pattern-following work: Dev, Infra, Data, QA

### Phase → Agent Mapping

| Phase | Entry Agent | Swarm Agents | PM Review | Key Deliverables |
|-------|-------------|-------------|-----------|------------------|
| Discovery | PM | PM, SA | Implicit (PM is in Swarm) | Project plan, requirements, initial architecture sketch |
| Architecture | SA | SA, Infra, Security | Post-Swarm step | Architecture diagrams, ADRs, cost estimates, security review |
| POC | Dev | Dev, Infra, Data, Security, SA | Post-Swarm step | Working POC, findings doc, updated architecture, security-reviewed IaC |
| Production | Dev | Dev, Infra, Data, Security, QA | Post-Swarm step | Production code, IaC, CI/CD, tests, security scans |
| Handoff | PM | PM, SA | Implicit (PM is in Swarm) | Documentation, runbooks, knowledge transfer |
| Retrospective | PM | PM, QA | N/A (internal) | Engagement analysis, lessons learned, pattern contributions, quality scores |

Note: Security was added to POC because Infra produces IaC during POC that must be reviewed. SA remains in POC to validate POC aligns with architecture. PM reviews every phase's output in a dedicated post-Swarm step (except Discovery and Handoff where PM is already the entry agent). Retrospective is internal — no customer approval gate.

---

## 5. Memory Architecture

### Layered Model

| Layer | Technology | Scope | Purpose |
|-------|-----------|-------|---------|
| **Working Memory** | Strands `invocation_state` | Single Swarm invocation | Shared config, DB connections, project_id, session IDs |
| **Short-Term Memory** | AgentCore Memory (STM) | Within a phase | Agent conversations during current phase work |
| **Long-Term Memory** | AgentCore Memory (LTM) with semantic + preference strategies | Cross-phase | Architecture decisions, customer preferences, lessons learned |
| **Task Ledger** | DynamoDB | Entire project | Structured record: decisions, assumptions, progress, blockers, customer feedback |
| **Project Artifacts** | Git repository | Entire project lifetime | Code, IaC, ADRs, docs — the canonical deliverables |
| **Semantic Search** | Bedrock Knowledge Base (S3 synced from Git) | Entire project lifetime | Any agent can search all artifacts semantically |
| **Cross-Engagement Metrics** | DynamoDB (`cloudcrew-metrics` table) | All projects | Engagement metrics, phase breakdowns, cost tracking, satisfaction trends |
| **Pattern Library** | S3 (`cloudcrew-patterns`) + Bedrock KB | All projects | Reusable IaC modules, code scaffolds, architecture patterns, security baselines |
| **Cross-Engagement LTM** | AgentCore Memory (shared namespace) | All projects | Lessons learned, best practices, engagement retrospective insights |

### Task Ledger Schema (DynamoDB)

The PM agent maintains a structured task ledger — inspired by Magentic-One's research on preventing context drift.

```
Table: cloudcrew-projects

PK: PROJECT#{project_id}
SK: LEDGER

Attributes:
  project_name: string
  customer: string
  current_phase: string (DISCOVERY | ARCHITECTURE | POC | PRODUCTION | HANDOFF)
  phase_status: string (IN_PROGRESS | AWAITING_APPROVAL | APPROVED | REVISION_REQUESTED)

  facts: list[{description, source, timestamp}]           # Verified information
  assumptions: list[{description, confidence, timestamp}]  # Unverified, needs validation
  decisions: list[{description, rationale, made_by, timestamp, adr_path}]
  blockers: list[{description, assigned_to, status, timestamp}]
  customer_feedback: list[{phase, decision, ratings: {quality, relevance, completeness}, feedback_text, timestamp}]

  deliverables: map{phase -> list[{name, git_path, status}]}

  step_function_execution_arn: string
  task_token: string  # Current waitForTaskToken token

  created_at: timestamp
  updated_at: timestamp
```

All agents can READ the ledger. Only the PM agent WRITES to it (prevents concurrent modification conflicts).

### Phase Transition Protocol

At every phase boundary:

1. Each active agent writes a **structured phase summary** using the phase summary template
2. PM agent consolidates summaries and updates the task ledger with: decisions made, assumptions validated/invalidated, deliverables produced
3. Working memory (STM) for the phase is **summarized into LTM** — raw conversation history is pruned
4. Durable decisions are **committed to Git** as ADRs
5. Step Functions passes **phase result JSON** (deliverable list, summary, open items) to the approval gate
6. Knowledge Base **re-syncs** from Git/S3 to index new artifacts

---

## 6. Artifact Templates (Structured Output Protocols)

Inspired by MetaGPT. Every deliverable type has a defined template. Agents produce outputs matching these schemas. Templates are included in system prompts.

| Template | Used By | Content |
|----------|---------|---------|
| Architecture Document | SA | Context, requirements, decisions, diagrams, trade-offs |
| ADR | SA | Title, Status, Context, Decision, Consequences (Nygard format) |
| Terraform Module | Infra | main.tf, variables.tf, outputs.tf, README.md |
| Test Plan | QA | Scope, test scenarios, acceptance criteria, results |
| Security Review | Security | Scope, findings with severity/remediation, pass/fail verdict |
| Phase Summary | All agents | Phase name, agents involved, work completed, decisions made, artifacts produced, open items |
| Project Plan | PM | Objectives, phases, workstreams, deliverables per phase, acceptance criteria |

---

## 7. Pairwise Review Cycles

Encoded in agent system prompts. Not left to emerge — explicitly mandated.

| Reviewer | Reviews | Trigger |
|----------|---------|---------|
| SA | Architecture-impacting code from Dev, Infra, Data | Any code that changes system boundaries, introduces new services, or modifies data flow |
| Security | ALL Terraform/IaC and IAM policies from Infra | Every IaC change before it's considered complete |
| Security | Auth/authz implementations from Dev | Any code handling authentication, authorization, or sensitive data |
| QA | ALL application code from Dev | Every feature before phase completion |
| Infra | CI/CD configurations | Pipeline changes |
| Data | Data access patterns from Dev | Database queries and data models |
| PM | ALL phase deliverables | Before presenting to customer for approval |

---

## 8. Error Handling and Failure Recovery

### Step Functions Error States

The state machine includes error handling at every phase:

```
Phase Swarm (ECS)
  ├── Success → PM Review → Approval Gate
  ├── Swarm Timeout → Retry with extended timeout (1x) → Fail → Notify Customer
  ├── ECS Task Failure → Retry (1x) → Fail → Notify Customer
  └── Interrupt Timeout → Save partial state → Notify Customer → Resume or Restart
```

Error handling rules:
- **Transient failures** (ECS crash, network error): Step Functions retries once automatically with the same input
- **Swarm timeout**: Retry once with extended timeout. If still fails, mark phase as FAILED, notify customer, allow manual restart
- **Agent error loops**: Swarm's `repetitive_handoff_detection` catches these; Swarm terminates and returns partial result. PM Review step flags incomplete deliverables.
- **Interrupt timeout**: If a within-phase interrupt goes unanswered for >30 minutes, the ECS task saves Swarm state, sends a reminder notification, and continues waiting. No automatic cancellation.

### Partial Phase Recovery

When a phase fails partway through:
1. Artifacts already committed to Git are preserved
2. Task ledger reflects last known state
3. Re-running the phase starts a fresh Swarm, but agents can read the existing artifacts and ledger to avoid re-doing completed work
4. PM Review step will flag which deliverables are missing

---

## 9. Project Lifecycle

### Project Kickoff

1. Customer logs into dashboard, clicks "New Project"
2. Dashboard presents SOW upload form (PDF, DOCX, or text)
3. API creates a new DynamoDB record (`PROJECT#{uuid}`, `SK: LEDGER`) with status `CREATED`
4. API starts a new Step Functions execution with `{project_id, sow_s3_path}`
5. Step Functions enters Discovery phase — PM agent parses the SOW
6. Customer is redirected to the project dashboard

API endpoint: `POST /projects` with SOW file upload.

### Chat Availability

The dashboard chat with PM is available **at all times**, not just during PM's active phases:

- **During PM's phases** (Discovery, Handoff): Messages go directly to the PM agent running in the Swarm
- **During other phases** (Architecture, POC, Production): Messages go to a **standalone PM agent instance** (not in the Swarm). This PM reads the task ledger and can answer status questions, relay customer feedback to the ledger, or interrupt the running Swarm if the customer has urgent input.
- **During approval gates**: Messages go to a standalone PM agent. Customer questions about deliverables are answered by PM reading the artifacts via `git_read`.

The standalone PM instance is a separate Lambda invocation — lightweight, request/response, not part of any Swarm.

### Two Repository Model

CloudCrew involves two separate Git repositories:

| Repo | Contents | Who writes |
|------|----------|-----------|
| **System repo** (`cloudcrew/`) | CloudCrew source code: agent definitions, tools, hooks, infrastructure, dashboard | Development team (human developers) |
| **Project repo** (`cloudcrew-project-{customer}/`) | Customer deliverables: architecture docs, ADRs, IaC, app code, tests, security reviews | CloudCrew agents via scoped Git tools |

Each customer engagement gets a fresh project repo. Agents never write to the system repo. The `PROJECT_REPO_URL` environment variable points to the customer's project repo.

---

## 10. Customer Dashboard

React SPA with three views:

### Chat View
- Real-time conversation with PM agent
- PM delegates to specialists for technical questions
- WebSocket via API Gateway for streaming responses (Strands `stream_async`)
- Message history persisted in AgentCore Memory

### Kanban Board
- Reads from DynamoDB task ledger
- Columns: Backlog | In Progress | Awaiting Review | Approved | Done
- Cards show: phase name, assigned agents, deliverables, status
- Approval actions: Approve / Request Changes (triggers Step Functions `SendTaskSuccess`/`SendTaskFailure`)
- Customer can add feedback comments when requesting changes

### Artifact Browser
- Lists deliverables from Git repo, organized by phase
- View inline (markdown, code) or download
- Shows file history (git log per file)
- Links to ADRs for architecture decisions

### Dashboard Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Vite |
| UI Components | Shadcn/ui |
| State/Data | TanStack Query |
| Real-time | WebSocket via API Gateway |
| Backend API | API Gateway + Lambda |
| Auth | Amazon Cognito |
| Hosting | CloudFront + S3 |

---

## 11. Technology Stack (Complete)

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Agent Framework | Strands Agents SDK | AWS-native, Swarm pattern, native interrupts, independent toolsets |
| Phase Orchestration | AWS Step Functions | Native HITL via `waitForTaskToken`, durable execution, visual debugging |
| Within-Phase Coordination | Strands Swarm | Emergent collaboration, explicit handoffs, review cycles |
| Within-Phase HITL | Strands Interrupts | Native interrupt/resume for clarifying questions |
| LLM (reasoning agents) | Amazon Bedrock — Claude Opus 4.6 | Deep reasoning for PM, SA, Security |
| LLM (execution agents) | Amazon Bedrock — Claude Sonnet | Efficient generation for Dev, Infra, Data, QA |
| Agent Memory (STM) | AgentCore Memory | Per-agent session memory within phases |
| Agent Memory (LTM) | AgentCore Memory (semantic + preference strategies) | Cross-phase decisions, customer preferences |
| Task Ledger | DynamoDB (`cloudcrew-projects`) | Structured project state, queryable by all agents |
| Engagement Metrics | DynamoDB (`cloudcrew-metrics`) | Cross-engagement performance tracking, cost analysis, satisfaction trends |
| Pattern Library | S3 (`cloudcrew-patterns`) + Bedrock KB | Reusable cross-engagement artifacts with tiered promotion |
| Project Artifacts | Git repository (GitHub) | Canonical deliverables, stigmergic coordination |
| Semantic Search | Bedrock Knowledge Bases (S3 data source) | Semantic search across all project artifacts |
| Phase Execution | ECS Fargate (AgentCore Runtime when mature) | Swarm invocations per phase; ECS required for >15min execution and interrupt blocking |
| Lightweight APIs | Lambda | Approval endpoints, chat relay, status queries, PM review step, standalone PM chat |
| Observability | AgentCore Observability + CloudWatch | Traces, metrics, logs, token usage |
| Customer API | API Gateway (REST + WebSocket) | Routes to Lambda handlers |
| Customer Dashboard | React SPA (CloudFront + S3) | Chat, kanban, artifact browser |
| Auth | Amazon Cognito | Customer login for dashboard |
| Diagram Generation | Python `diagrams` library + Mermaid | Architecture diagrams as code |
| IaC | Terraform | Infrastructure as code for customer deliverables |
| Security Scanning | Checkov | IaC security validation |
| Tool Connectivity | AgentCore Gateway + MCP | External tool access for agents |

---

## 12. Self-Improvement System

CloudCrew gets better with every engagement through a cross-engagement intelligence layer. Five mechanisms feed improvement:

### Pattern Library

A tiered repository of reusable artifacts stored in S3 (`cloudcrew-patterns`) and indexed by a dedicated Bedrock KB data source.

| Tier | Criteria | Who promotes |
|------|----------|-------------|
| **Draft** | Auto-captured from engagement artifacts at retrospective | System (automatic) |
| **Candidate** | Used once and worked well | Any agent contributes |
| **Proven** | Used in 3+ engagements with >80% success rate | QA agent promotes |

Pattern categories: `iac/`, `architecture/`, `security/`, `code/`. Each pattern is a directory containing the artifact files plus a `metadata.json` with tier, usage count, success rate, tags, and contributing agent.

Agent tools for the pattern library:
- `search_patterns(query, category?, tags?)` — semantic search via Bedrock KB
- `use_pattern(pattern_id)` — copies pattern into project repo, increments usage count
- `contribute_pattern(artifact_path, category, tags)` — creates draft pattern from engagement artifact
- `promote_pattern(pattern_id)` — QA agent only, promotes candidate → proven

Agents search the pattern library **before building from scratch** in every phase.

### Engagement Metrics

A dedicated DynamoDB table (`cloudcrew-metrics`, PAY_PER_REQUEST) tracks quantitative data per engagement:

- **Per-engagement summary**: total token cost, duration, revision cycles, handoffs, satisfaction score, patterns used/contributed
- **Per-phase breakdown**: token cost, duration, revision cycles, handoffs, per-agent cost breakdown
- **Cross-engagement timeline**: all engagements sorted by date for trend analysis
- **Post-engagement survey**: overall satisfaction, would-reuse, improvement areas

A Strands hook (`metrics_hook`) runs on every agent invocation to track token usage, turn count, and handoff events. Data flows from working memory → phase aggregation (PM Review Lambda) → engagement aggregation (Finalize Metrics Lambda at retrospective).

### Structured Customer Feedback

At each approval gate, the dashboard collects structured ratings alongside the approve/revise decision:

- Quality (1-5), Relevance (1-5), Completeness (1-5)
- Optional freeform notes

After Handoff, a post-engagement survey captures overall satisfaction, reuse intent, and improvement suggestions. All feedback is stored in the metrics table and factored into pattern success rates and engagement trend analysis.

### Retrospective Phase

After Handoff approval, a Retrospective phase runs automatically (no customer approval gate):

- **PM agent**: Compares outcomes vs. SOW, summarizes lessons learned, identifies artifacts for pattern library, writes insights to cross-engagement LTM
- **QA agent**: Scores deliverable quality, evaluates pattern candidates for promotion, promotes qualifying patterns

Followed by a **Finalize Metrics Lambda** that aggregates all phase metrics, writes the cross-engagement timeline item, and triggers KB re-sync for newly contributed patterns.

### Cost Tracking

Token costs are attributed by agent, phase, and deliverable. The metrics hook records `{model_id, input_tokens, output_tokens}` per call. A utility maps model → price-per-token. The retrospective generates a cost report identifying expensive agents, high-cost phases, and optimization opportunities (e.g., "consider Sonnet instead of Opus for routine SA documentation").

---

## 13. Design Principles

1. **Orchestration for structure, choreography for creativity** — Step Functions handles the predictable (phase ordering, approvals). Swarm handles the creative (agent collaboration within phases).

2. **Explicit over implicit** — Agents use explicit handoff messages with context, not implicit coordination through artifacts alone. Both channels (direct handoff + Git artifacts) are needed.

3. **Scoped capabilities** — Each agent gets only the tools for its domain. The Infra agent cannot edit application code. The Dev agent cannot modify Terraform. This prevents agents from acting outside their expertise.

4. **Structured outputs** — Every deliverable follows a defined template. This constrains LLM drift and ensures downstream agents get consistent inputs.

5. **Pairwise review** — Review patterns encoded in system prompts. SA reviews architecture-impacting changes. Security reviews all IaC. QA reviews all application code. Not left to emerge — explicitly mandated.

6. **Context management is critical** — Agents must RETRIEVE relevant context before acting. Every agent has Knowledge Base search tool. Phase summaries prevent context window exhaustion. LTM preserves cross-phase decisions.

7. **Failure recovery through re-planning** — When agents fail, re-invoke the Swarm with error context. Phase outputs are revisable (living documents in Git). Maintain enough state to resume from last good checkpoint.

8. **Task ledger as ground truth** — PM agent maintains a structured ledger of facts, assumptions, decisions, and blockers. All agents read it. This prevents the "lost context" problem across phases.

---

## 14. Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Framework | Strands Agents | AWS-native, Swarm+Graph patterns, native interrupts, AgentCore ecosystem |
| Phase orchestration | Step Functions (not Strands Graph) | Durable HITL via `waitForTaskToken`; projects span weeks/months |
| Within-phase HITL | Strands native interrupts | Minutes-timescale clarifications without breaking Swarm context |
| Between-phase HITL | Step Functions `waitForTaskToken` | Hours/days-timescale approvals with durable persistence |
| Agent count | 7 (PM, SA, Infra, Dev, Data, Security, QA) | AgentVerse validates 5-7 as near-optimal team size |
| LLM models | Opus 4.6 for reasoning, Sonnet for execution | Cost/quality balance; single Bedrock API key during testing |
| Task tracking | DynamoDB task ledger (Magentic-One pattern) | Prevents context drift; structured facts/assumptions/decisions |
| Artifact format | Structured templates (MetaGPT SOP pattern) | Prevents hallucination drift; consistent downstream input |
| Review patterns | Explicit pairwise (ChatDev pattern) | Quality improvement over single-pass generation |
| Shared workspace | Git repository | Stigmergic coordination (swarm intelligence) + durable audit trail |
| Phase execution | ECS Fargate (not Lambda) | Swarm timeouts exceed Lambda 15-min limit; interrupt blocking requires long-lived process |
| PM review step | Dedicated post-Swarm step | PM isn't in every Swarm but must validate all deliverables against SOW |
| Security in POC | Security added to POC Swarm | Infra produces IaC during POC that must be security-reviewed |
| Chat availability | Standalone PM Lambda for non-PM phases | Customer needs PM access at all times, not just during PM's active Swarms |
| Customer UI | React SPA (chat + kanban + artifacts) | Familiar patterns; straightforward to build |
| Metrics storage | Separate DynamoDB table (`cloudcrew-metrics`) | Clearer separation from task ledger; no GSIs needed; same cost |
| Pattern storage | S3 + Bedrock KB | Files in S3 for storage, KB for semantic search; consistent with project artifact search |
| Retrospective phase | Automated (no approval gate) | Internal analysis doesn't need customer input; runs PM + QA |
| Metrics collection | Strands hook (in-process) | More accurate than external monitoring; writes to working memory during Swarm |
| Self-improvement milestone | M6 (after Dashboard) | Core system must work before it can improve itself |
