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

### Live Demo (No Installation Required)

**🎮 [Try the Interactive Demo →](https://jjricks6.github.io/CloudCrew/)**

Watch a full engagement unfold in your browser:
- Architecture → POC → Production → Handoff phases
- Real-time agent collaboration visualization
- Interactive phase reviews with artifact preview
- Chat interface for Q&A during review
- Confetti celebration on engagement completion 🎉

**Demo features:**
- Full agent collaboration simulation
- Phase timeline with progress tracking
- Artifact browser and download capability
- PM chat during review phases
- Zero backend required

---

## Getting Started

Pick your path:

| Goal | Start Here |
|------|-----------|
| **See it work live** | [Interactive Demo](https://jjricks6.github.io/CloudCrew/) — 5 min, no setup |
| **Understand the architecture** | [Architecture Deep-Dive](docs/architecture/final-architecture.md) |
| **Deploy to AWS** | [Deployment Guide](docs/architecture/implementation-guide.md#deployment) |
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
| **LLM API calls** | Amazon Bedrock (Claude 3.5 Sonnet) | Serverless model access; $3/MTok input, $15/MTok output; no infrastructure management |
| **Memory** | AgentCore Memory (STM/LTM) | Persistent memory across agent invocations; search via Bedrock KB |
| **Task ledger** | DynamoDB | Immutable task record; global view of project state |
| **Artifacts** | Git repository | Version control for all deliverables; audit trail |
| **Dashboard** | React SPA | Real-time agent activity, phase timeline, artifact browser, chat |

### Cost & Operations

**Monthly Baseline:** ~$60-130 (dev environment with Bedrock LLM calls)

- Infrastructure (Step Functions, Fargate, DynamoDB, etc.): ~$50
- Bedrock LLM calls (5-50M tokens during development): ~$10-80

**AWS Resources Deployed:**

| Resource | Quantity | Monthly Cost | Notes |
|----------|----------|--------------|-------|
| **Step Functions** | 1 state machine | ~$2-5 | $0.000025 per state transition; typical project ~200-400 transitions |
| **ECS Fargate** | On-demand tasks | ~$15-25 | 2 vCPU × 4GB RAM × 20 min/phase × 5 phases; scales with project complexity |
| **DynamoDB** | 2 tables (task ledger, rate limits) | ~$5-10 | On-demand pricing; no provisioned capacity; TTL auto-cleanup |
| **ECR** | 1 repository | <$1 | Private container registry for phase runner image |
| **S3** | 1 Terraform state bucket | <$1 | Remote state storage; minimal size |
| **CloudWatch Logs** | 50-200 GB/month | ~$15-25 | Logs from ECS tasks, Lambda, Step Functions; 30-day retention |
| **X-Ray** | 1-10M traces/month | ~$5-10 | Distributed tracing for agent execution and handoffs |
| **Bedrock (Claude 3.5)** | 5-50M tokens/month | ~$10-50 | LLM API calls for agent reasoning; $3/MTok input, $15/MTok output |
| **VPC / Networking** | 1 VPC, public subnets | Free | No NAT Gateways (dev cost optimization); public subnets acceptable for dev |
| **RDS (optional)** | None by default | $0 | Project uses DynamoDB; RDS available if needed |

**Per-Project Cost:** ~$20-80 depending on phase complexity and execution time.
- Infrastructure (ECS, Step Functions): ~$5-15 per project
- Bedrock LLM calls (agent reasoning): ~$15-65 per project (varies by system prompt depth and phase count)

**Cost Optimization (Built-in):**
- On-demand DynamoDB (not provisioned capacity) scales automatically
- Public subnets eliminate NAT Gateway costs ($32-48/month each)
- ECS Fargate on-demand (no always-on container services)
- Step Functions task token approach eliminates Lambda duration overruns
- Automatic CloudWatch Logs TTL and S3 lifecycle policies

**Deployment:** Manual (Terraform) — CI never applies infrastructure. See [Deployment Guide](docs/architecture/implementation-guide.md#deployment).

**Scaling:** Step Functions handles project queuing; Fargate scales task count; DynamoDB on-demand pricing scales usage.

**Observability:** CloudWatch Logs, X-Ray traces, custom metrics dashboard.

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

**Backend Development:**
```bash
# Terminal 1: Backend server
python -m src.phases.runner --project-id demo --sow-file sow.md

# Terminal 2: Dashboard (connects to backend)
cd dashboard && npm run dev
```

**Try the demo without setup:**
- Visit [https://jjricks6.github.io/CloudCrew/](https://jjricks6.github.io/CloudCrew/) for the live interactive demo

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
