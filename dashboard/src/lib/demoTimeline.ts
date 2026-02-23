/**
 * Pure data: scripted event sequences for the demo engine.
 *
 * Each phase has a "playbook" with work, interrupt, resume, and approval
 * segments. The engine plays them sequentially, pausing for user input
 * at interrupts and approvals.
 */

import type { KanbanColumn, WebSocketEvent } from "./types";
import type { ReviewStep } from "@/state/stores/phaseReviewStore";

export interface TimelineStep {
  delayMs: number;
  event: WebSocketEvent;
}

/** A complete phase playbook the engine can execute generically. */
export interface PhasePlaybook {
  phase: string;
  workSegment: TimelineStep[];
  interrupt?: {
    id: string;
    question: string;
  };
  resumeSegment: TimelineStep[];
  approvalQuestion: string;
  reviewSteps: ReviewStep[];
}

// ---------------------------------------------------------------------------
// Helpers (phase-parameterized)
// ---------------------------------------------------------------------------

function a(phase: string, agent: string, detail: string, delayMs = 0): TimelineStep {
  return { delayMs, event: { event: "agent_active", project_id: "demo", phase, agent_name: agent, detail } };
}

function h(phase: string, from: string, to: string, delayMs = 200): TimelineStep {
  return { delayMs, event: { event: "handoff", project_id: "demo", phase, agent_name: to, detail: `Handoff from ${from} to ${to}` } };
}

function tu(phase: string, taskId: string, status: KanbanColumn, delayMs = 0): TimelineStep {
  return { delayMs, event: { event: "task_updated", project_id: "demo", phase, task_id: taskId, updates: { status } } };
}

function dc(phase: string, name: string, gitPath: string, version: string, delayMs = 0): TimelineStep {
  return { delayMs, event: { event: "deliverable_created", project_id: "demo", phase, name, git_path: gitPath, version } };
}

// ---------------------------------------------------------------------------
// ARCHITECTURE
// ---------------------------------------------------------------------------

const ARCH_WORK: TimelineStep[] = [
  a("ARCHITECTURE", "Solutions Architect", "Researching serverless patterns for multi-tenant SaaS", 0),
  tu("ARCHITECTURE", "demo-t3", "in_progress", 500),
  a("ARCHITECTURE", "Solutions Architect", "Designing API Gateway integration patterns", 7000),
  h("ARCHITECTURE", "Solutions Architect", "Data Engineer", 6000),
  a("ARCHITECTURE", "Data Engineer", "Designing DynamoDB single-table schema and access patterns", 2000),
  tu("ARCHITECTURE", "demo-t4", "in_progress", 500),
  a("ARCHITECTURE", "Data Engineer", "Mapping entity relationships to GSI projections", 8000),
  dc("ARCHITECTURE", "Data Model", "docs/data-model.md", "v0.1", 500),
  h("ARCHITECTURE", "Data Engineer", "Solutions Architect", 6000),
  a("ARCHITECTURE", "Solutions Architect", "Integrating data model into system architecture", 2000),
  h("ARCHITECTURE", "Solutions Architect", "Security Engineer", 5000),
  a("ARCHITECTURE", "Security Engineer", "Reviewing authentication approach and IAM policies", 2000),
  tu("ARCHITECTURE", "demo-t6", "in_progress", 500),
  a("ARCHITECTURE", "Security Engineer", "Evaluating Cognito token scoping and network boundaries", 8000),
  h("ARCHITECTURE", "Security Engineer", "Solutions Architect", 6000),
  a("ARCHITECTURE", "Solutions Architect", "Evaluating search requirements for data model", 2000),
  tu("ARCHITECTURE", "demo-t6", "review", 0),
];

const ARCH_RESUME: TimelineStep[] = [
  a("ARCHITECTURE", "Project Manager", "Relaying customer response to the team", 0),
  h("ARCHITECTURE", "Project Manager", "Solutions Architect", 1000),
  a("ARCHITECTURE", "Solutions Architect", "Incorporating customer feedback into architecture", 2000),
  dc("ARCHITECTURE", "System Architecture", "docs/architecture.md", "v0.1", 500),
  h("ARCHITECTURE", "Solutions Architect", "Developer", 6000),
  a("ARCHITECTURE", "Developer", "Defining OpenAPI contracts for REST endpoints", 2000),
  tu("ARCHITECTURE", "demo-t8", "in_progress", 500),
  a("ARCHITECTURE", "Developer", "Documenting request/response schemas and error formats", 7000),
  dc("ARCHITECTURE", "API Contracts", "docs/api-contracts.md", "v0.1", 500),
  h("ARCHITECTURE", "Developer", "Solutions Architect", 5000),
  tu("ARCHITECTURE", "demo-t8", "review", 0),
  h("ARCHITECTURE", "Solutions Architect", "QA Engineer", 3000),
  a("ARCHITECTURE", "QA Engineer", "Creating test strategy for serverless architecture", 2000),
  tu("ARCHITECTURE", "demo-t9", "in_progress", 500),
  a("ARCHITECTURE", "QA Engineer", "Defining coverage targets and test categories", 6000),
  dc("ARCHITECTURE", "Test Strategy", "docs/test-strategy.md", "v0.1", 500),
  h("ARCHITECTURE", "QA Engineer", "Solutions Architect", 5000),
  tu("ARCHITECTURE", "demo-t9", "review", 0),
  h("ARCHITECTURE", "Solutions Architect", "Security Engineer", 3000),
  a("ARCHITECTURE", "Security Engineer", "Final security audit of architecture design", 2000),
  tu("ARCHITECTURE", "demo-t6", "done", 0),
  a("ARCHITECTURE", "Security Engineer", "Architecture security review — all findings addressed", 6000),
  dc("ARCHITECTURE", "Data Model", "docs/data-model.md", "v1.0", 500),
  dc("ARCHITECTURE", "System Architecture", "docs/architecture.md", "v1.0", 300),
  dc("ARCHITECTURE", "API Contracts", "docs/api-contracts.md", "v1.0", 300),
  dc("ARCHITECTURE", "Test Strategy", "docs/test-strategy.md", "v1.0", 300),
  tu("ARCHITECTURE", "demo-t3", "done", 2000),
  tu("ARCHITECTURE", "demo-t4", "done", 500),
  tu("ARCHITECTURE", "demo-t5", "done", 500),
  tu("ARCHITECTURE", "demo-t7", "done", 500),
  tu("ARCHITECTURE", "demo-t8", "done", 300),
  tu("ARCHITECTURE", "demo-t9", "done", 300),
];

// ---------------------------------------------------------------------------
// POC
// ---------------------------------------------------------------------------

const POC_WORK: TimelineStep[] = [
  a("POC", "Developer", "Setting up Cognito user pool and identity provider", 0),
  tu("POC", "demo-t10", "in_progress", 500),
  h("POC", "Developer", "Infrastructure", 7000),
  a("POC", "Infrastructure", "Provisioning staging VPC and Lambda functions", 2000),
  tu("POC", "demo-t11", "in_progress", 500),
  a("POC", "Infrastructure", "Deploying API Gateway and DynamoDB tables", 8000),
  h("POC", "Infrastructure", "Developer", 6000),
  a("POC", "Developer", "Implementing login and signup API endpoints", 2000),
  tu("POC", "demo-t14", "in_progress", 500),
  a("POC", "Developer", "Connecting frontend auth flow to Cognito", 9000),
  dc("POC", "Auth Proof-of-Concept", "poc/auth-poc.md", "v0.1", 500),
  h("POC", "Developer", "QA Engineer", 5000),
  a("POC", "QA Engineer", "Running baseline load test against staging API", 2000),
  tu("POC", "demo-t15", "in_progress", 500),
  a("POC", "QA Engineer", "Analyzing latency distribution — p95 at 183ms", 11000),
  dc("POC", "Load Test Results", "poc/load-test-results.md", "v0.1", 500),
];

const POC_RESUME: TimelineStep[] = [
  a("POC", "Project Manager", "Relaying latency decision to the team", 0),
  h("POC", "Project Manager", "Developer", 1000),
  a("POC", "Developer", "Adding provisioned concurrency to Lambda functions", 2000),
  h("POC", "Developer", "QA Engineer", 8000),
  a("POC", "QA Engineer", "Re-running load test with optimizations", 2000),
  a("POC", "QA Engineer", "Latency targets met — p95 at 142ms", 7000),
  dc("POC", "Load Test Results", "poc/load-test-results.md", "v1.0", 500),
  tu("POC", "demo-t15", "review", 0),
  h("POC", "QA Engineer", "Security Engineer", 5000),
  a("POC", "Security Engineer", "Scanning PoC for OWASP Top 10 vulnerabilities", 2000),
  tu("POC", "demo-t16", "in_progress", 500),
  a("POC", "Security Engineer", "Validating Cognito token scoping and rotation", 8000),
  dc("POC", "Auth Proof-of-Concept", "poc/auth-poc.md", "v1.0", 300),
  dc("POC", "Migration Runbook Draft", "poc/migration-runbook.md", "v1.0", 300),
  tu("POC", "demo-t16", "done", 0),
  tu("POC", "demo-t10", "done", 1000),
  tu("POC", "demo-t11", "done", 500),
  tu("POC", "demo-t14", "done", 500),
  tu("POC", "demo-t15", "done", 500),
];

// ---------------------------------------------------------------------------
// PRODUCTION
// ---------------------------------------------------------------------------

const PROD_WORK: TimelineStep[] = [
  a("PRODUCTION", "Developer", "Implementing row-level tenant isolation", 0),
  tu("PRODUCTION", "demo-t12", "in_progress", 500),
  a("PRODUCTION", "Developer", "Building tenant context propagation middleware", 10000),
  h("PRODUCTION", "Developer", "Data Engineer", 6000),
  a("PRODUCTION", "Data Engineer", "Creating ETL pipeline for legacy PostgreSQL migration", 2000),
  tu("PRODUCTION", "demo-t17", "in_progress", 500),
  a("PRODUCTION", "Data Engineer", "Running schema mapping for 47 tables", 12000),
  h("PRODUCTION", "Data Engineer", "Infrastructure", 5000),
  a("PRODUCTION", "Infrastructure", "Configuring blue-green deployment with CodeDeploy", 2000),
  tu("PRODUCTION", "demo-t18", "in_progress", 500),
  dc("PRODUCTION", "Deployment Guide", "production/deployment-guide.md", "v0.1", 500),
  a("PRODUCTION", "Infrastructure", "Setting up CloudWatch dashboards and alarms", 9000),
  tu("PRODUCTION", "demo-t19", "in_progress", 500),
  dc("PRODUCTION", "Monitoring Configuration", "production/monitoring.md", "v0.1", 500),
  h("PRODUCTION", "Infrastructure", "Security Engineer", 7000),
  a("PRODUCTION", "Security Engineer", "Running penetration test against staging", 2000),
  tu("PRODUCTION", "demo-t20", "in_progress", 500),
  a("PRODUCTION", "Security Engineer", "Validating PCI-DSS compliance boundaries", 11000),
  h("PRODUCTION", "Security Engineer", "Data Engineer", 5000),
  a("PRODUCTION", "Data Engineer", "Running migration dry run — found 12 schema mismatches", 2000),
];

const PROD_RESUME: TimelineStep[] = [
  a("PRODUCTION", "Project Manager", "Relaying migration decision to the team", 0),
  h("PRODUCTION", "Project Manager", "Data Engineer", 1000),
  a("PRODUCTION", "Data Engineer", "Applying compatibility layer for schema mismatches", 2000),
  a("PRODUCTION", "Data Engineer", "Re-running migration — all 47 tables validated", 10000),
  dc("PRODUCTION", "Data Migration Report", "production/migration-report.md", "v1.0", 500),
  tu("PRODUCTION", "demo-t17", "done", 0),
  h("PRODUCTION", "Data Engineer", "QA Engineer", 5000),
  a("PRODUCTION", "QA Engineer", "Running end-to-end regression suite", 2000),
  tu("PRODUCTION", "demo-t21", "in_progress", 500),
  a("PRODUCTION", "QA Engineer", "All 287 test cases passed — zero regressions", 9000),
  tu("PRODUCTION", "demo-t21", "done", 0),
  dc("PRODUCTION", "Deployment Guide", "production/deployment-guide.md", "v1.0", 300),
  dc("PRODUCTION", "Monitoring Configuration", "production/monitoring.md", "v1.0", 300),
  tu("PRODUCTION", "demo-t12", "done", 1000),
  tu("PRODUCTION", "demo-t18", "done", 500),
  tu("PRODUCTION", "demo-t19", "done", 500),
  tu("PRODUCTION", "demo-t20", "done", 500),
];

// ---------------------------------------------------------------------------
// HANDOFF (no interrupt — smooth finish)
// ---------------------------------------------------------------------------

const HANDOFF_WORK: TimelineStep[] = [
  a("HANDOFF", "Infrastructure", "Writing operations runbook and incident procedures", 0),
  tu("HANDOFF", "demo-t13", "in_progress", 500),
  h("HANDOFF", "Infrastructure", "Developer", 9000),
  dc("HANDOFF", "Operations Runbook", "handoff/operations-runbook.md", "v1.0", 500),
  a("HANDOFF", "Developer", "Generating OpenAPI documentation with examples", 2000),
  tu("HANDOFF", "demo-t22", "in_progress", 500),
  a("HANDOFF", "Developer", "Documenting error codes and rate limiting details", 8000),
  dc("HANDOFF", "API Documentation", "handoff/api-docs.md", "v1.0", 500),
  tu("HANDOFF", "demo-t22", "done", 0),
  h("HANDOFF", "Developer", "Security Engineer", 5000),
  a("HANDOFF", "Security Engineer", "Compiling PCI-DSS evidence package", 2000),
  tu("HANDOFF", "demo-t24", "in_progress", 500),
  a("HANDOFF", "Security Engineer", "Finalizing SOC 2 control mappings", 10000),
  dc("HANDOFF", "Compliance Report", "handoff/compliance-report.md", "v1.0", 500),
  tu("HANDOFF", "demo-t24", "done", 0),
  h("HANDOFF", "Security Engineer", "Solutions Architect", 5000),
  a("HANDOFF", "Solutions Architect", "Preparing architecture walkthrough session", 2000),
  tu("HANDOFF", "demo-t25", "in_progress", 500),
  tu("HANDOFF", "demo-t23", "in_progress", 300),
  a("HANDOFF", "Solutions Architect", "Running knowledge transfer session 1 of 3", 8000),
  a("HANDOFF", "Solutions Architect", "Completing knowledge transfer — all sessions done", 7000),
  dc("HANDOFF", "Training Materials", "handoff/training-materials.md", "v1.0", 500),
  tu("HANDOFF", "demo-t13", "done", 1000),
  tu("HANDOFF", "demo-t23", "done", 500),
  tu("HANDOFF", "demo-t25", "done", 500),
];

// ---------------------------------------------------------------------------
// Phase Playbooks — consumed by the demo engine
// ---------------------------------------------------------------------------

export const PHASE_PLAYBOOKS: PhasePlaybook[] = [
  {
    phase: "ARCHITECTURE",
    workSegment: ARCH_WORK,
    interrupt: {
      id: "demo-int-arch",
      question:
        "The architecture uses a single DynamoDB table. Should we add a dedicated search index (OpenSearch) for full-text search, or is DynamoDB + GSIs sufficient for the MVP?",
    },
    resumeSegment: ARCH_RESUME,
    approvalQuestion:
      "The **Architecture** phase is complete. All deliverables have been drafted and reviewed by the team. Please review the artifacts and let us know if you'd like to approve and move to the next phase, or if you have feedback.",
    reviewSteps: [
      {
        id: "arch-step-1",
        type: "summary",
        title: "What We Accomplished",
        content:
          "Our team completed a comprehensive analysis of your system requirements and designed a serverless architecture tailored to your needs.\n\n" +
          "We focused on three key areas:\n" +
          "1. **System design** — how components interact and scale\n" +
          "2. **Data modeling** — efficient DynamoDB schema with flexible queries\n" +
          "3. **Security** — IAM policies, authentication, and compliance baseline",
      },
      {
        id: "arch-step-2",
        type: "decisions",
        title: "Key Architectural Decisions",
        content:
          "**Why Serverless?**\n" +
          "- Auto-scaling without managing servers\n" +
          "- Cost-efficient for variable workloads\n" +
          "- Faster deployment and iteration\n\n" +
          "**Database Design:**\n" +
          "- Single DynamoDB table with Global Secondary Indexes\n" +
          "- Supports all query patterns without over-provisioning\n" +
          "- Trade-off: requires careful access pattern design\n\n" +
          "**Authentication:**\n" +
          "- AWS Cognito for user management\n" +
          "- JWT tokens for stateless API authorization\n" +
          "- Prevents session state management overhead",
      },
      {
        id: "arch-step-3",
        type: "artifacts",
        title: "Deliverables & Documentation",
        content:
          "### Documents Ready for Review\n\n" +
          "- **System Architecture** — Complete design diagram with all components\n" +
          "- **Data Model** — DynamoDB schema with access patterns documented\n" +
          "- **API Contracts** — OpenAPI spec defining all endpoints\n" +
          "- **Test Strategy** — Coverage targets for serverless architecture\n" +
          "- **Security Review** — IAM policies and threat modeling results\n\n" +
          "All documents are available in the Artifacts tab.",
      },
    ],
  },
  {
    phase: "POC",
    workSegment: POC_WORK,
    interrupt: {
      id: "demo-int-poc",
      question:
        "Load testing shows p95 latency at 183ms — just under our 200ms target. Should we optimize now with provisioned concurrency (~$80/month), or accept the current numbers and optimize later if needed?",
    },
    resumeSegment: POC_RESUME,
    approvalQuestion:
      "The **Proof of Concept** phase is complete. Auth integration, API prototype, and load testing are all validated. Security scan passed with zero critical findings. Ready to proceed to Production?",
    reviewSteps: [
      {
        id: "poc-step-1",
        type: "summary",
        title: "Proof of Concept Results",
        content:
          "We successfully implemented a working authentication system and validated core performance characteristics of your architecture.\n\n" +
          "**What We Built:**\n" +
          "- Complete login and signup flow using AWS Cognito\n" +
          "- Token refresh mechanism for seamless user sessions\n" +
          "- API prototype with core endpoints functional\n\n" +
          "**What We Validated:**\n" +
          "- Performance under load (2x expected traffic)\n" +
          "- Security scanning for vulnerabilities\n" +
          "- Network isolation and access controls",
      },
      {
        id: "poc-step-2",
        type: "decisions",
        title: "Performance & Optimization Decisions",
        content:
          "**Initial Load Test Results:**\n" +
          "- p95 latency: 183ms (slightly above 200ms target)\n" +
          "- Throughput: 800 concurrent users\n" +
          "- Errors: None\n\n" +
          "**Optimization Applied:**\n" +
          "- Added provisioned concurrency to Lambda functions\n" +
          "- Increased memory allocation for faster execution\n" +
          "- Cost impact: ~$80/month additional\n\n" +
          "**After Optimization:**\n" +
          "- p95 latency: 142ms (29% improvement, exceeds target)\n" +
          "- Throughput: 1,000+ concurrent users sustained\n" +
          "- Errors: None during 8-hour stress test",
      },
      {
        id: "poc-step-3",
        type: "artifacts",
        title: "Deliverables & Test Reports",
        content:
          "### Key Deliverables\n\n" +
          "- **Auth Proof-of-Concept** — Full login/signup/refresh flow documented\n" +
          "- **Load Test Results** — Detailed performance metrics and graphs\n" +
          "- **Security Scan Report** — OWASP Top 10 analysis (0 critical findings)\n" +
          "- **Migration Runbook Draft** — Initial procedures for production migration\n\n" +
          "All reports are ready for your review in the Artifacts section.",
      },
    ],
  },
  {
    phase: "PRODUCTION",
    workSegment: PROD_WORK,
    interrupt: {
      id: "demo-int-prod",
      question:
        "During the migration dry run, we found 12 records with schema mismatches between PostgreSQL and DynamoDB. Should we add a compatibility layer to handle edge cases automatically, or clean up the source data before migrating?",
    },
    resumeSegment: PROD_RESUME,
    approvalQuestion:
      "The **Production** phase is complete. Data migration finished with zero data loss, blue-green deployment is live, and all 287 regression tests passed. Monitoring dashboards are active. Ready to proceed to Handoff?",
    reviewSteps: [
      {
        id: "prod-step-1",
        type: "summary",
        title: "Production Deployment Success",
        content:
          "Your system is now live! We successfully migrated all data, deployed to production using blue-green deployment, and validated end-to-end functionality.\n\n" +
          "**Deployment Approach:**\n" +
          "- Blue-green deployment strategy enabled zero-downtime cutover\n" +
          "- Old system (blue) and new system (green) running in parallel\n" +
          "- Instant rollback capability if issues detected\n" +
          "- Actual cutover took 2 minutes with no service interruption",
      },
      {
        id: "prod-step-2",
        type: "decisions",
        title: "Data Migration & Testing Decisions",
        content:
          "**Data Migration Strategy:**\n" +
          "- Initial dry run revealed 12 schema mismatches\n" +
          "- Chose: Build compatibility layer vs. clean source data\n" +
          "- Added automatic schema transformation for edge cases\n" +
          "- Final run: 2.8M records migrated with 100% data integrity\n\n" +
          "**Testing & Validation:**\n" +
          "- All 287 regression tests passed\n" +
          "- Performance benchmarks: 2x improvement vs. legacy\n" +
          "- No errors during 48-hour stability testing\n\n" +
          "**Operational Readiness:**\n" +
          "- CloudWatch dashboards monitoring 23 key metrics\n" +
          "- Alarms configured for critical thresholds\n" +
          "- Auto-scaling tested and active",
      },
      {
        id: "prod-step-3",
        type: "artifacts",
        title: "Production Documentation & Compliance",
        content:
          "### Deployment & Operations Documentation\n\n" +
          "- **Data Migration Report** — Complete records of 2.8M migrations\n" +
          "- **Deployment Guide** — Blue-green procedures for future updates\n" +
          "- **Monitoring Configuration** — CloudWatch setup and alert thresholds\n" +
          "- **Regression Test Results** — All 287 tests with performance profiles\n" +
          "- **Compliance Report** — PCI-DSS validation evidence\n\n" +
          "30-day post-launch support period is now active.",
      },
    ],
  },
  {
    phase: "HANDOFF",
    workSegment: HANDOFF_WORK,
    resumeSegment: [],
    approvalQuestion:
      "The **Handoff** phase is complete. Operations runbook, API documentation, training materials, and compliance report have all been delivered. Three knowledge transfer sessions are complete. Ready to close the engagement?",
    reviewSteps: [
      {
        id: "handoff-step-1",
        type: "summary",
        title: "Knowledge Transfer Complete",
        content:
          "We've completed comprehensive knowledge transfer to ensure your team can confidently operate and maintain the system independently.\n\n" +
          "**Training Sessions Completed:**\n" +
          "- Session 1: Architecture walkthrough with your engineering leads\n" +
          "- Session 2: Operations procedures and incident response\n" +
          "- Session 3: API integration and custom extension patterns\n\n" +
          "**Team Feedback:**\n" +
          "- All participants confident with core operations\n" +
          "- Q&A sessions recorded for future reference\n" +
          "- Scheduled follow-up session in 2 weeks",
      },
      {
        id: "handoff-step-2",
        type: "decisions",
        title: "Support & Compliance Strategy",
        content:
          "**30-Day Post-Launch Support:**\n" +
          "- Dedicated channel for critical issues\n" +
          "- Response time: 1 hour for production incidents\n" +
          "- Email support for non-critical questions\n" +
          "- Weekly health check calls\n\n" +
          "**Compliance & Certifications:**\n" +
          "- PCI-DSS compliance evidence package provided\n" +
          "- SOC 2 Type II control mappings documented\n" +
          "- Audit trail and logging configured\n" +
          "- Data retention policies configured per requirements\n\n" +
          "**Long-Term Support:**\n" +
          "- Knowledge base searchable and indexed\n" +
          "- All documentation in your GitHub organization\n" +
          "- Custom SLA available for extended support",
      },
      {
        id: "handoff-step-3",
        type: "artifacts",
        title: "Documentation & Resources",
        content:
          "### Complete Handoff Package\n\n" +
          "- **Operations Runbook** — 25+ procedures for daily operations and emergencies\n" +
          "- **API Documentation** — Complete endpoint reference with code examples\n" +
          "- **Compliance Report** — PCI-DSS and SOC 2 evidence and attestations\n" +
          "- **Training Materials** — Recorded sessions and slide decks\n" +
          "- **Troubleshooting Guide** — Common issues and resolutions\n" +
          "- **Knowledge Base** — Searchable FAQs and architectural decisions\n\n" +
          "All resources are available in the secure team portal.",
      },
    ],
  },
];

// Legacy exports for backward compatibility with checkpoints
export const SEED_SEGMENT: TimelineStep[] = [];
