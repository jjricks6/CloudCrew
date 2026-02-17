# Architecture Recommendation: Graph of Swarms

Research conducted: 2026-02-16

## Proposed Pattern

A **Graph** manages phase-level orchestration (deterministic, with approval gates), and within each phase a **Swarm** allows agents to self-organize and collaborate.

```
Graph (Phase-level orchestration)
│
├── Node: "Discovery"
│   └── Swarm(PM, SA)
│   └── Deliverables: Project plan, requirements doc, initial architecture sketch
│   └── [Customer Approval Gate]
│
├── Node: "Architecture"
│   └── Swarm(SA, Infra, Security)
│   └── Deliverables: Architecture diagrams, ADRs, cost estimates, security review
│   └── [Customer Approval Gate]
│
├── Node: "POC"
│   └── Swarm(Dev, Infra, Data, SA)
│   └── Deliverables: Working POC, findings doc, updated architecture
│   └── [Customer Approval Gate]
│
├── Node: "Production"
│   └── Swarm(Dev, Infra, Data, Security, QA)
│   └── Deliverables: Production code, IaC, CI/CD, tests, security scans
│   └── [Customer Approval Gate]
│
└── Node: "Handoff"
    └── Swarm(PM, SA)
    └── Deliverables: Documentation, runbooks, knowledge transfer materials
```

### Why this pattern?

- **Graph** gives deterministic phase ordering — Discovery MUST complete before Architecture, etc.
- **Conditional edges** implement approval gates — next phase only starts when customer approves
- **Swarm** within each phase allows emergent collaboration — SA might hand off to Infra agent who discovers a security concern and hands off to Security agent
- **Nested pattern** is natively supported by Strands (Swarm as a node in a Graph)

---

## Agent Roster

### PM Agent (Project Manager / Orchestrator)

**Role:** Owns the SOW, decomposes into workstreams, tracks progress, manages customer communication.

**Phases active:** Discovery, Handoff (primary), all others (advisory)

**Tools:**
- SOW parser / requirements extractor
- Project plan generator
- Task tracker (DynamoDB read/write)
- Customer communication tool (format and present deliverables)
- Git tools (read project-plan.md, write updates)

**System prompt guidance:**
- You are the project manager for an AWS cloud engagement
- Your job is to decompose the SOW into actionable work, assign work to specialists, and ensure deliverables meet acceptance criteria
- Always validate deliverables against SOW requirements before presenting to the customer

### SA Agent (Solutions Architect)

**Role:** Designs technical architecture, makes technology decisions, produces architecture docs and diagrams.

**Phases active:** Discovery, Architecture (primary), POC (advisory), Production (advisory), Handoff

**Tools:**
- Architecture diagram generator (Mermaid, Python `diagrams` library, or similar)
- AWS service reference / documentation lookup
- Architecture Decision Record (ADR) writer
- Cost estimation tool (AWS Pricing Calculator API)
- Git tools (read/write docs/architecture/)
- Knowledge Base search (search existing project context)

**System prompt guidance:**
- You are a senior AWS Solutions Architect
- Design for production from the start: multi-AZ, least privilege, encryption at rest and in transit
- Document every significant decision as an ADR with context, options considered, and rationale
- Produce diagrams for every major architectural component

### Infra Agent (Cloud Infrastructure Engineer)

**Role:** Writes IaC (Terraform), sets up networking, security groups, CI/CD pipelines.

**Phases active:** Architecture (advisory), POC, Production (primary)

**Tools:**
- Terraform code generator and validator
- Terraform plan/apply (sandboxed)
- Checkov security scanner
- AWS provider documentation lookup
- Git tools (read/write infra/)
- Architecture doc reader (to understand what to build)

**System prompt guidance:**
- You are a senior DevOps/Infrastructure engineer specializing in AWS
- All infrastructure must be defined as Terraform code — no manual console actions
- Follow AWS Well-Architected Framework principles
- Always run Checkov scans before considering IaC complete

### Dev Agent (Application Developer)

**Role:** Builds application code, APIs, frontends, microservices.

**Phases active:** POC, Production (primary)

**Tools:**
- Code generation and editing tools
- Test runner
- Linter / formatter
- Git tools (read/write app/)
- Architecture doc reader
- Package manager tools (npm, pip, etc.)

**System prompt guidance:**
- You are a senior full-stack developer
- Write clean, well-tested code following the language/framework best practices
- Every feature needs unit tests at minimum
- Follow the architecture design produced by the SA agent

### Data Agent (Data Engineer)

**Role:** Databases, data modeling, ETL pipelines, data stores.

**Phases active:** POC, Production (primary)

**Tools:**
- Database schema design tools
- SQL / NoSQL query tools
- Data pipeline generator (Glue, Step Functions, etc.)
- Git tools (read/write data/)
- Architecture doc reader

**System prompt guidance:**
- You are a senior data engineer specializing in AWS data services
- Design data models that support the application's access patterns
- Consider scalability, backup/recovery, and data lifecycle from the start

### Security Agent

**Role:** Reviews all code and IaC for security posture, runs scans, ensures guardrails.

**Phases active:** Architecture (advisory), Production (primary — review gate)

**Tools:**
- Checkov / tfsec for IaC scanning
- OWASP dependency check
- IAM policy analyzer
- Security review checklist tool
- Git tools (read everything, write security/)

**System prompt guidance:**
- You are a senior security engineer
- Review all code and infrastructure for OWASP Top 10, CIS benchmarks, and AWS security best practices
- Flag any use of overly permissive IAM policies, unencrypted resources, or public-facing services without WAF
- Produce a security findings report for each review

### QA Agent

**Role:** Writes and executes test plans, validates deliverables against acceptance criteria.

**Phases active:** Production (primary)

**Tools:**
- Test framework tools (pytest, jest, etc.)
- Integration test runner
- Load testing tools
- Test report generator
- Git tools (read everything, write app/tests/)

**System prompt guidance:**
- You are a senior QA engineer
- Write test plans based on acceptance criteria from the SOW and architecture docs
- Cover unit, integration, and end-to-end test scenarios
- Report test results with pass/fail and coverage metrics

---

## Approval Gate Mechanism

### Design

Since Strands doesn't have a native `interrupt()` like LangGraph, we build approval gates using:

1. **Graph conditional edges** — next phase only traverses if previous phase approved
2. **AfterNodeCallEvent hook** — detects phase completion and writes approval request
3. **DynamoDB** — stores approval state
4. **Customer-facing API/UI** — customer reviews deliverables and approves
5. **Polling or EventBridge** — graph resumes when approval arrives

### Flow

```
Phase Swarm completes
    ↓
AfterNodeCallEvent hook fires
    ↓
Hook writes to DynamoDB:
  PK: PROJECT#123, SK: PHASE#architecture
  status: AWAITING_APPROVAL
  deliverables: [list of git paths]
    ↓
Customer-facing API shows pending approval
Customer reviews deliverables (reads from Git)
Customer approves or requests changes
    ↓
If approved:
  DynamoDB updated: status → APPROVED
  Graph conditional edge checks DynamoDB → returns True
  Next phase begins
    ↓
If changes requested:
  DynamoDB updated: status → REVISION_REQUESTED, feedback → "..."
  Current phase Swarm re-invoked with feedback context
  Agents address feedback
  Back to AWAITING_APPROVAL
```

### Implementation sketch

```python
# Conditional edge function
def phase_approved(required_phase: str):
    def check(state: GraphState) -> bool:
        # Check DynamoDB for approval
        response = dynamodb.get_item(
            TableName="cloudcrew-projects",
            Key={"PK": f"PROJECT#{project_id}", "SK": f"PHASE#{required_phase}"}
        )
        return response.get("Item", {}).get("status") == "APPROVED"
    return check

# Graph edges
builder.add_edge("discovery", "architecture", condition=phase_approved("discovery"))
builder.add_edge("architecture", "poc", condition=phase_approved("architecture"))
builder.add_edge("poc", "production", condition=phase_approved("poc"))
builder.add_edge("production", "handoff", condition=phase_approved("production"))
```

### Alternative: Step Functions for approval gates

AWS Step Functions `.waitForTaskToken` provides native HITL:

```
Step Functions (phases)
├── Discovery (invoke Strands Swarm)
├── Wait for Approval (.waitForTaskToken)
├── Architecture (invoke Strands Swarm)
├── Wait for Approval (.waitForTaskToken)
├── POC (invoke Strands Swarm)
├── ...
```

**Trade-off:** More infrastructure but native approval gates without custom polling.

---

## Customer Interaction Model

### Phase gates (structured)

At the end of each phase:
1. PM agent compiles deliverables summary
2. System presents to customer via API/UI
3. Customer reviews and provides structured feedback (approve / request changes / ask questions)

### Mid-phase steering (ad-hoc)

Customer can interject at any time:
- "Actually, we need multi-tenant support"
- "Can we use Aurora instead of DynamoDB?"

These messages go to the PM agent, which:
1. Assesses impact on current work
2. Updates the project plan
3. Communicates changes to active agents via shared memory
4. If the change is fundamental, may restart the current phase Swarm with updated context

### Direct technical questions

Customer may ask technical questions directly:
- Route through PM agent which delegates to the appropriate specialist
- Or expose individual agents via A2A for direct customer access (advanced)

---

## Technology Stack Summary

| Component | Technology |
|-----------|------------|
| Agent Framework | Strands Agents SDK |
| Multi-agent Orchestration | Strands Graph (phases) + Swarm (within phases) |
| LLM | Amazon Bedrock (Claude) |
| Agent Memory (STM) | AgentCore Memory |
| Agent Memory (LTM) | AgentCore Memory with semantic + preference strategies |
| Project Knowledge Base | Bedrock Knowledge Bases |
| Artifact Store | Git repository |
| Phase/Approval State | DynamoDB |
| Approval Gate | Custom (hooks + DynamoDB + API) or Step Functions |
| Agent Deployment | AgentCore Runtime or ECS/Lambda |
| Observability | AgentCore Observability + CloudWatch |
| Customer UI | API Gateway + frontend (TBD) |
| Tool Connectivity | AgentCore Gateway + MCP |
| Diagram Generation | Python `diagrams` library or Mermaid |
| IaC | Terraform |
| Security Scanning | Checkov |

---

## Open Questions for Further Research

1. **Agent-to-agent within a Swarm** — How well do Strands Swarms handle 5+ agents? What are the practical limits on `max_handoffs` before quality degrades?

2. **Approval gate latency** — If we use Graph conditional edges with DynamoDB polling, what's the polling mechanism? Do we block the Graph execution or use an external trigger?

3. **Cost management** — Each agent invocation uses LLM tokens. A full project lifecycle could consume millions of tokens. How do we estimate and control costs?

4. **Concurrent workstreams** — Can we run multiple phases partially in parallel (e.g., start POC for a simple component while architecture continues for a complex one)?

5. **Agent quality control** — How do we validate that an agent's output is good enough before presenting to the customer? Peer review via another agent? Automated checks?

6. **Customer UI/UX** — What does the customer-facing interface look like? Chat? Dashboard? PR review model?

7. **Error recovery** — What happens when an agent fails mid-task? How do we recover without losing work?

8. **SOW parsing** — How do we reliably extract structured requirements from an unstructured SOW document?

9. **Diagram generation** — What tools produce the best architecture diagrams programmatically? Mermaid? Python diagrams? Draw.io XML?

10. **Testing the agents** — How do we test and validate agent behavior before deploying to a real customer engagement?
