# CloudCrew

> **AI-powered delivery team that autonomously executes software projects from requirements to production.**
>
> 7 specialized agents (PM, Solutions Architect, Infrastructure, Development, Data, Security, QA) collaborate through phased delivery with durable approval gates. Zero coordination overhead — agents handoff work, self-organize, and produce Git-versioned artifacts at every decision point.

---

## What CloudCrew Does

Given a Statement of Work, CloudCrew autonomously delivers:

- **Architecture Phase** — System design, ADRs, cost estimates, security review
- **POC Phase** — Working proof of concept with load testing and security validation
- **Production Phase** — Production code, IaC, CI/CD pipelines, test suites
- **Handoff Phase** — Documentation, runbooks, and knowledge transfer materials

All artifacts are reviewed by the customer at phase gates. If revision is needed, agents re-run with feedback. No human coordination required within phases — the Swarm self-organizes.

---

## Three Pillars

### 🤝 Multi-Agent Autonomy
Agents specialize by domain (architecture, infrastructure, security, etc.) and coordinate through natural handoffs. No centralized orchestration—**agents decide when to hand off work based on task completion**, not static workflows. This mirrors how real teams operate.

### 🔄 Durable Orchestration
Built on AWS Step Functions with `waitForTaskToken` approval gates. If a customer takes time to review, the entire project state is preserved. If a phase fails mid-way, execution resumes from the last checkpoint—**no lost work**.

### 📝 Transparent Artifacts
Every decision is Git-versioned. ADRs explain tradeoffs. Code is production-quality. Security reviews are documented. Customers can audit the full decision trail and understand not just **what** was built, but **why**.

---

## Quick Look

### Demo Mode (No Backend Required)

```bash
# Clone and install
git clone https://github.com/jjricks6/CloudCrew.git
cd CloudCrew
source .venv/bin/activate
cd dashboard && npm install

# Run demo (browser-based simulation)
npm run dev

# Watch the Architecture → POC → Production → Handoff phases
# Review phase completions, chat with PM, approve to progress
```

**Demo features:**
- Full agent collaboration simulation
- Interactive phase reviews with artifact preview
- Chat interface for Q&A during review
- Confetti celebration on engagement completion 🎉

### Real Mode (With Backend Deployment)

```bash
# Deploy AWS infrastructure (one-time)
make tf-init
make tf-plan
make tf-apply

# Run backend agent server
python -m src.phases.runner \
  --project-id my-project \
  --sow-file sow.md

# Access dashboard at http://localhost:5173
```

---

## Getting Started

Pick your path:

| Goal | Start Here |
|------|-----------|
| **Understand what CloudCrew does** | [Quick Demo](#demo-mode-no-backend-required) — 5 min |
| **See it work without deployment** | [Run Dashboard Demo](#demo-mode-no-backend-required) — 10 min |
| **Deploy to AWS** | [Deployment Guide](docs/architecture/implementation-guide.md#deployment) |
| **Build custom agents** | [Agent Development](docs/architecture/agent-specifications.md) |
| **Understand the architecture** | [Architecture Deep-Dive](docs/architecture/final-architecture.md) |
| **Contribute or extend** | [Contributing Guide](#contributing) |

---

## Architecture at a Glance

### Two-Tier Orchestration

```
AWS Step Functions (hours/days timescale)
├── Phase: Discovery
│   └── Swarm: PM + SA (agent handoffs, minutes timescale)
├── Approval Gate: Customer reviews deliverables
├── Phase: Architecture
│   └── Swarm: SA + Infra + Security
├── Approval Gate
├── Phase: POC
│   └── Swarm: Dev + Infra + Data + Security + SA
├── Approval Gate
├── Phase: Production
│   └── Swarm: Dev + Infra + Data + Security + QA
├── Approval Gate
├── Phase: Handoff
│   └── Swarm: PM + SA
└── Retrospective (internal, no approval)
```

**Tier 1 — Phase Orchestration (Step Functions):**
Manages project lifecycle as a state machine. Phases execute sequentially with durable approval gates using `waitForTaskToken`. Customers review phase deliverables; if approved, next phase begins; if revision needed, agents re-run with feedback.

**Tier 2 — Within-Phase Collaboration (Strands Swarm):**
Agents run as a Swarm, enabling emergent collaboration. Agents hand off work based on task completion (not pre-configured workflows), review each other's outputs, and self-organize within a 20-minute execution budget per phase.

### Infrastructure

| Component | Technology | Why |
|-----------|-----------|-----|
| **Phase orchestration** | AWS Step Functions | Durable state machine; supports long-lived approval gates |
| **Agent execution** | ECS Fargate | Swarms exceed Lambda's 15-min limit; persistent connection needed for interrupts |
| **Agents & handoffs** | Strands Agents SDK | Native support for agent coordination, tool use, and interrupts |
| **Memory** | AgentCore Memory (STM/LTM) | Persistent memory across agent invocations; search via Bedrock KB |
| **Task ledger** | DynamoDB | Immutable task record; global view of project state |
| **Artifacts** | Git repository | Version control for all deliverables; audit trail |
| **Dashboard** | React SPA | Real-time agent activity, phase timeline, artifact browser, chat |

### Cost & Operations

| Aspect | Details |
|--------|---------|
| **Monthly baseline** | ~$50 (dev environment) with on-demand DynamoDB, no NAT Gateways, public subnets |
| **Per-project cost** | ~$10-30 depending on phase complexity and execution time |
| **Deployment** | Manual (Terraform) — CI never applies infrastructure. See [Deployment Guide](docs/architecture/implementation-guide.md#deployment). |
| **Scaling** | Step Functions handles project queuing; Fargate scales task count; DynamoDB on-demand pricing scales usage |
| **Observability** | CloudWatch Logs, X-Ray traces, custom metrics dashboard |

---

## How It Works: A Complete Example

### Scenario: E-Commerce Platform Migration

**Input:** SOW requesting serverless migration of legacy monolith to AWS.

**Phase 1: Discovery**
- PM and SA collaborate to create project charter and initial requirements
- PM generates comprehensive project plan
- Deliverable: 5-page project plan, requirement specs, initial architecture sketch
- **Customer reviews and approves**

**Phase 2: Architecture**
- SA leads; Infra and Security agents provide input
- SA writes ADRs: "Why Lambda + API Gateway vs. App Runner?" (with cost and scaling justification)
- Infra provides Terraform module library recommendations
- Security performs threat model and compliance review
- Deliverable: Architecture diagrams, 12 ADRs, cost estimates, security review
- **Customer reviews and approves**

**Phase 3: POC**
- Dev builds working auth integration + sample endpoint
- Data architect designs database schema and migration strategy
- Infra provisions dev environment and sets up CI/CD foundation
- QA writes test plan; Security scans code and IaC
- Deliverable: Working POC repo, load test results (2x expected traffic), security scan findings
- **Customer reviews and approves**

**Phase 4: Production**
- Dev implements full system with all features
- Infra builds blue-green deployment, monitoring, and auto-recovery
- Data executes migration with validation; QA runs 287 regression tests
- Security performs final penetration test
- Deliverable: Production code, IaC, CI/CD pipeline, 287 tests, security report
- **Customer reviews and approves**

**Phase 5: Handoff**
- PM compiles operations runbook
- SA creates API documentation
- Training materials prepared; 3 knowledge transfer sessions held
- Deliverable: Full runbooks, API docs, troubleshooting guide, PCI-DSS compliance report
- **Customer reviews and approves**

**Result:** 5 weeks of autonomous delivery, fully auditable, zero surprises. All artifacts in Git. Customer has complete knowledge transfer.

---

## Key Features

### ✅ Autonomous Phase Execution
- Agents collaborate without human intervention within each phase
- Natural handoffs based on task completion (not static DAGs)
- Self-organizing team structure that mirrors real software teams

### ✅ Durable Approval Gates
- Project state preserved across restarts
- Customers can take time to review without losing progress
- Revision requests trigger re-execution with feedback context

### ✅ Transparent Decisions
- Every decision documented as an ADR
- Architecture choices explained with tradeoffs and justifications
- Full Git history for audit trail

### ✅ Production-Quality Output
- Code passes security scans, linting, type checking
- IaC passes Checkov compliance checks
- Tests provide >90% coverage
- CI/CD pipelines ready-to-use

### ✅ Real-Time Observability
- Watch agents collaborate in real-time dashboard
- See agent activity, handoffs, and decision reasoning
- Chat with agents during execution for clarifications

### ✅ Interactive Customer Reviews
- Review phase deliverables before approving
- Ask PM questions during review phase
- Browse artifacts, download documents
- Approve or request changes with context

---

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/jjricks6/CloudCrew.git
cd CloudCrew

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
cd dashboard && npm install && cd ..

# Run tests
make check  # All checks: format, lint, typecheck, test, security, Terraform validate
```

### Running Locally

**Demo Mode (No AWS Required):**
```bash
cd dashboard && npm run dev
# Simulates full agent collaboration without backend
```

**With Local Backend:**
```bash
# Terminal 1: Backend
python -m src.phases.runner --project-id demo --sow-file sow.md

# Terminal 2: Dashboard
cd dashboard && npm run dev
```

### Development Workflow

1. **Make changes** to agents, tools, or dashboard
2. **Run checks:** `make check` (format, lint, typecheck, test, security, size)
3. **Fix any failures** — don't commit code that fails checks
4. **Commit with conventional message:** `feat(agents): add PM tool` or `fix(tools): handle git errors`
5. **Push and open PR** — CI runs full test suite

### Code Quality

- **430+ unit tests** with 91%+ coverage
- **Strict type checking** (mypy) across all Python
- **Security scanning** (Bandit) for vulnerability detection
- **Lint checks** (Ruff) for code quality
- **Infrastructure-as-code validation** (Terraform + Checkov)

---

## Architecture Deep-Dive

### Agents & Specialization

| Agent | Responsibilities | Tools |
|-------|-----------------|-------|
| **PM** | Project planning, requirements management, approval reviews | SOW parsing, task ledger management, deliverable compilation |
| **Solutions Architect** | System design, architecture documentation, ADRs | Architecture templates, cost analysis tools |
| **Infrastructure** | IaC, CI/CD, deployment pipelines | Terraform templates, AWS provider knowledge |
| **Development** | Feature implementation, code quality | Git operations, code review tools |
| **Data** | Database design, data pipeline architecture | Schema templates, migration tools |
| **Security** | Threat modeling, security reviews, compliance | Security scanning tools, vulnerability databases |
| **QA** | Test strategy, coverage analysis, release readiness | Test generation tools, coverage reporting |

### State Management

**Global State (DynamoDB Task Ledger):**
- Project metadata, current phase, approval status
- Phase deliverables and metrics
- Customer feedback and revision context
- TTL-based automatic cleanup

**Agent Memory (AgentCore Memory):**
- Short-term memory: Current task context, recent decisions
- Long-term memory: Pattern library, learned patterns from past projects
- Search capability via Bedrock Knowledge Base

**Artifact Versioning (Git):**
- Every deliverable committed with timestamp
- Immutable audit trail
- Rollback capability if needed

---

## Deployment

### Prerequisites

- AWS account with appropriate IAM permissions
- Terraform 1.5+
- Python 3.12+
- Node.js 18+

### One-Time Setup

```bash
# 1. Deploy bootstrap infrastructure (S3 state bucket, DynamoDB lock table)
make tf-init  # Creates remote state
make tf-bootstrap

# 2. Deploy main infrastructure
cd infra/terraform
make tf-plan
make tf-apply

# 3. Build and push Docker image for ECS
make docker-build
make docker-push
```

### Cost Management

CloudCrew is designed for **cost efficiency** in dev/testing:

- **On-demand DynamoDB** (not provisioned capacity)
- **No NAT Gateways** (dev uses public subnets)
- **No ECS services** (Step Functions launches tasks on-demand)
- **Estimated cost:** $50/month baseline + $10-30 per project

**Important:** Run `make tf-destroy` after testing to tear down resources and minimize costs.

For detailed deployment guide, see [Deployment Guide](docs/architecture/implementation-guide.md#deployment).

---

## Troubleshooting

### Agent Stalls or Doesn't Progress

**Check task execution:**
```bash
# View latest project state
python -m src.state.ledger --project-id <id>

# Check agent logs in CloudWatch
aws logs tail /aws/ecs/cloudcrew-phase-runner --follow
```

**Check for rate limiting:**
- Verify DynamoDB throttling isn't occurring
- Check CloudWatch metrics for task count

### Phase Approval Gate Timeout

**If customer hasn't approved after 7 days:**
```bash
# Get task token from Step Functions
aws stepfunctions describe-execution --execution-arn <arn>

# Send heartbeat to keep alive
aws stepfunctions send-task-heartbeat --task-token <token>

# Or send success/failure
aws stepfunctions send-task-success --task-token <token> --task-output '{}'
```

### Dashboard Can't Connect to Backend

**Check WebSocket connection:**
```bash
# Verify API endpoint is correct in dashboard/.env
API_URL=http://localhost:8000

# Check backend is running
lsof -i :8000
```

---

## Documentation

| Document | Purpose |
|----------|---------|
| [Final Architecture](docs/architecture/final-architecture.md) | Definitive architecture reference with state machine, phases, and design decisions |
| [Agent Specifications](docs/architecture/agent-specifications.md) | Agent roles, capabilities, system prompts, tool access |
| [Implementation Guide](docs/architecture/implementation-guide.md) | Setup, deployment, cost management, troubleshooting |
| [ADR Index](docs/architecture/) | Architectural decision records for all major choices |
| [Research Documents](docs/research/) | Framework comparison, memory architecture, coordination patterns |

---

## Contributing

### Adding a New Agent

See [Agent Development Guide](docs/architecture/agent-specifications.md#adding-new-agents).

```python
# agents/my_agent.py
from strands import Agent

class MyAgent(Agent):
    """Agent that does X."""

    def __init__(self):
        super().__init__(
            name="MyAgent",
            model_id="claude-opus-4-6",
            system_prompt="You are an expert in X...",
            tools=[tool1, tool2],
        )
```

### Adding a New Tool

See [Tool Development Guide](docs/architecture/implementation-guide.md#adding-tools).

### Reporting Bugs

1. Check [existing issues](https://github.com/jjricks6/CloudCrew/issues)
2. Create a new issue with:
   - Reproduction steps
   - Expected vs. actual behavior
   - CloudWatch logs (if applicable)
   - Your environment (Python version, OS, AWS region)

### Proposing Features

1. Open a discussion in [Discussions](https://github.com/jjricks6/CloudCrew/discussions)
2. Describe the use case and desired behavior
3. If accepted, create an ADR to document the decision

---

## License

This project is proprietary. See [LICENSE](LICENSE) for details.

---

## Support

- **Documentation:** [docs/](docs/)
- **Issues:** [GitHub Issues](https://github.com/jjricks6/CloudCrew/issues)
- **Discussions:** [GitHub Discussions](https://github.com/jjricks6/CloudCrew/discussions)

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

**Built with [Strands Agents SDK](https://docs.strands.com) | Deployed on [AWS](https://aws.amazon.com) | Inspired by [real software teams](https://en.wikipedia.org/wiki/Agile_software_development)**
