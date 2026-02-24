/**
 * Pure data: scripted PM onboarding questions and demo SOW content.
 *
 * Each step defines a PM question, an input placeholder, whether file
 * upload is allowed, and a canned demo answer (used for auto-fill or
 * display when the user submits without typing).
 */

export interface OnboardingStep {
  /** The PM's question text (streamed character-by-character in demo). */
  question: string;
  /** Placeholder hint for the text input. Empty = no input (SOW step). */
  placeholder: string;
  /** Whether to show the file upload zone for this step. */
  allowUpload: boolean;
  /** Auto-filled answer in demo mode. Empty = no user input expected. */
  demoAnswer: string;
}

export const ONBOARDING_STEPS: OnboardingStep[] = [
  {
    question:
      "Welcome to CloudCrew! I'm your Project Manager and I'll be guiding your team of AI specialists through your project. Let's get started — what would you like to name your project?",
    placeholder: "e.g., Customer Portal Modernization",
    allowUpload: false,
    demoAnswer: "E-Commerce Platform Migration",
  },
  {
    question:
      "Great choice! Can you give me a brief overview of the project goals? What problem are you solving, and what does success look like?",
    placeholder: "Describe your project goals...",
    allowUpload: true,
    demoAnswer:
      "We need to migrate our legacy e-commerce platform from on-prem to AWS. Success means 99.9% uptime, sub-200ms API latency, and zero data loss during the migration window.",
  },
  {
    question:
      "That's clear. Tell me about your current technical environment — what AWS services are you already using, and what does your team look like?",
    placeholder: "Describe your current setup and team...",
    allowUpload: true,
    demoAnswer:
      "We have 3 AWS accounts (dev/staging/prod). Currently running EC2 instances behind an ALB with RDS PostgreSQL. Team is 4 backend developers, 1 DevOps engineer, no dedicated architect.",
  },
  {
    question:
      "Got it. Are there any compliance requirements, security constraints, or hard deadlines I should factor into the plan?",
    placeholder: "Security, compliance, timeline constraints...",
    allowUpload: true,
    demoAnswer:
      "PCI-DSS compliance required for payment processing. SOC 2 Type II certification is in progress. Target go-live is Q3 2026 — we have a contractual obligation with our largest retail partner.",
  },
  {
    question:
      "Thank you — I have a good picture of your project. Let me prepare a Statement of Work for your review.",
    placeholder: "",
    allowUpload: false,
    demoAnswer: "",
  },
];

/**
 * Demo SOW content — realistic markdown shown in the SowReviewCard.
 * Incorporates details from the demo answers above.
 */
/** PM wrap-up message — streamed after the user accepts the SOW. */
export const WRAPUP_MESSAGE =
  "Excellent — the SOW is locked in and your project is officially underway! " +
  "Here's how things will work from here:\n\n" +
  "Your CloudCrew team of 7 specialists — architecture, infrastructure, development, " +
  "data, security, and QA — will begin the Discovery phase immediately. " +
  "You'll see their progress on the dashboard in real time.\n\n" +
  "At key milestones I'll ask for your review and approval before we move to the next phase. " +
  "If anything comes up that needs your input, I'll flag it and you'll see a notification.\n\n" +
  "If you ever want to discuss changes, ask questions, or adjust priorities, " +
  "just message me in the Chat panel — I'm always here.\n\n" +
  "Let's build something great.";

/** Standalone revision step — shown when the user requests SOW changes. */
export const REVISION_STEP: OnboardingStep = {
  question:
    "Of course — what changes would you like me to make to the Statement of Work?",
  placeholder: "Describe the changes you'd like…",
  allowUpload: false,
  demoAnswer:
    "Can we extend the PoC phase to 3 weeks and add a dedicated performance testing milestone?",
};

export const DEMO_SOW_CONTENT = `# Statement of Work

## Project: E-Commerce Platform Migration

### Objective
Migrate the existing on-premises e-commerce platform to AWS with zero data loss,
99.9% uptime SLA, and sub-200ms API latency. The migration must maintain PCI-DSS
compliance throughout and complete before the Q3 2026 contractual deadline.

### Scope

**Phase 1 — Discovery** (1 week)
- Audit current EC2/RDS architecture across 3 AWS accounts
- Map all data flows for PCI-DSS compliance boundaries
- Interview stakeholders and document integration points
- Deliverables: Requirements document, architecture assessment, risk register

**Phase 2 — Architecture** (2 weeks)
- Design target-state architecture (ECS Fargate, Aurora PostgreSQL, ElastiCache)
- Plan network topology with VPC peering across dev/staging/prod
- Define IAM policies, encryption strategy, and security group rules
- Deliverables: Architecture decision records, infrastructure diagrams, data model

**Phase 3 — Proof of Concept** (2 weeks)
- Implement authentication flow with Cognito + existing user base
- Stand up staging environment with IaC (Terraform)
- Validate latency targets with load testing
- Deliverables: Working PoC, load test results, migration runbook draft

**Phase 4 — Production** (3 weeks)
- Implement full migration with blue-green deployment strategy
- Configure monitoring, alerting, and auto-scaling
- Execute data migration with rollback capability
- Deliverables: Production deployment, monitoring dashboards, runbooks

**Phase 5 — Handoff** (1 week)
- Knowledge transfer sessions with your DevOps team
- Documentation review and gap closure
- Post-migration support plan
- Deliverables: Operations handbook, training materials, support SLA

### Team
| Role | Responsibility |
|------|---------------|
| Project Manager | Coordination, timeline, customer communication |
| Solutions Architect | System design, architecture decisions |
| Developer | Application migration, API implementation |
| Infrastructure Engineer | IaC, networking, CI/CD pipelines |
| Data Engineer | Data migration, ETL pipelines |
| Security Engineer | Compliance, IAM, encryption, auditing |
| QA Engineer | Testing strategy, load testing, validation |

### Timeline
- **Start date:** Upon approval
- **Target completion:** 9 weeks
- **Go-live deadline:** Q3 2026

### Assumptions
- AWS accounts are accessible with appropriate IAM permissions
- Existing database schema documentation is available
- Development team is available for knowledge transfer sessions
- No major schema changes required during migration
`;
