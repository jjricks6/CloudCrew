/**
 * Demo mode — simulates backend behavior so the dashboard works without
 * deployed infrastructure.  Activated when the projectId is "demo".
 */

import type { BoardTask, ChatMessage, DeliverableItem, Phase, ProjectStatus, TaskUpdateFields, WebSocketEvent } from "./types";
import { PHASE_ORDER } from "./types";

// ---------------------------------------------------------------------------
// Detection
// ---------------------------------------------------------------------------

export function isDemoMode(projectId: string | undefined): boolean {
  return projectId === "demo";
}

// ---------------------------------------------------------------------------
// Mock project status
// ---------------------------------------------------------------------------

export const DEMO_PROJECT_STATUS: ProjectStatus = {
  project_id: "demo",
  project_name: "E-Commerce Migration",
  current_phase: "ARCHITECTURE" as Phase,
  phase_status: "IN_PROGRESS",
  deliverables: {},
  facts: [
    {
      description: "Customer needs a multi-tenant SaaS platform",
      source: "Discovery phase interview",
      timestamp: "2025-06-01T10:00:00Z",
    },
  ],
  assumptions: [
    {
      description: "Customer traffic will not exceed 10k requests/minute at launch",
      confidence: "MEDIUM",
      timestamp: "2025-06-01T11:00:00Z",
    },
  ],
  decisions: [
    {
      description: "Use serverless architecture with API Gateway + Lambda",
      rationale: "Lower operational overhead, pay-per-use pricing",
      made_by: "Solutions Architect",
      timestamp: "2025-06-02T14:00:00Z",
      adr_path: "",
    },
  ],
  blockers: [],
  created_at: "2025-06-01T09:00:00Z",
  updated_at: new Date().toISOString(),
};

// ---------------------------------------------------------------------------
// Mock board tasks (kanban board)
// ---------------------------------------------------------------------------

export const DEMO_BOARD_TASKS: BoardTask[] = [
  {
    task_id: "demo-t1",
    title: "Gather stakeholder requirements",
    description:
      "Interview key stakeholders to identify functional and non-functional requirements for the SaaS platform.",
    phase: "DISCOVERY",
    status: "done",
    assigned_to: "pm",
    comments: [
      {
        author: "pm",
        content: "Completed all 3 stakeholder interviews. Key findings documented.",
        timestamp: "2025-06-01T12:00:00Z",
      },
    ],
    artifact_path: "docs/requirements.md",
    created_at: "2025-06-01T09:00:00Z",
    updated_at: "2025-06-01T12:00:00Z",
  },
  {
    task_id: "demo-t2",
    title: "Define data model requirements",
    description: "Identify entities, relationships, and access patterns for the data layer.",
    phase: "DISCOVERY",
    status: "done",
    assigned_to: "data",
    comments: [
      {
        author: "data",
        content: "Identified 8 core entities with access patterns documented.",
        timestamp: "2025-06-01T14:00:00Z",
      },
    ],
    artifact_path: "",
    created_at: "2025-06-01T09:30:00Z",
    updated_at: "2025-06-01T14:00:00Z",
  },
  {
    task_id: "demo-t3",
    title: "Design system architecture",
    description:
      "Create high-level architecture design following AWS Well-Architected Framework principles.",
    phase: "ARCHITECTURE",
    status: "in_progress",
    assigned_to: "sa",
    comments: [
      {
        author: "sa",
        content: "Evaluating serverless vs container-based approaches. Leaning serverless for lower ops overhead.",
        timestamp: "2025-06-02T10:00:00Z",
      },
      {
        author: "sa",
        content: "Decision: API Gateway + Lambda for API layer. ADR-001 written.",
        timestamp: "2025-06-02T14:00:00Z",
      },
    ],
    artifact_path: "docs/architecture.md",
    created_at: "2025-06-02T09:00:00Z",
    updated_at: "2025-06-02T14:00:00Z",
  },
  {
    task_id: "demo-t4",
    title: "Design data model",
    description:
      "Create DynamoDB table designs with access patterns, GSIs, and entity schemas.",
    phase: "ARCHITECTURE",
    status: "in_progress",
    assigned_to: "data",
    comments: [
      {
        author: "data",
        content: "Single-table design with 3 GSIs. Working on tenant isolation pattern.",
        timestamp: "2025-06-02T11:00:00Z",
      },
    ],
    artifact_path: "docs/data-model.md",
    created_at: "2025-06-02T09:00:00Z",
    updated_at: "2025-06-02T11:00:00Z",
  },
  {
    task_id: "demo-t5",
    title: "Write ADR: Authentication approach",
    description: "Evaluate Cognito vs custom auth and document the decision.",
    phase: "ARCHITECTURE",
    status: "review",
    assigned_to: "sa",
    comments: [
      {
        author: "sa",
        content: "ADR-002 drafted. Recommending Cognito with JWT tokens.",
        timestamp: "2025-06-02T13:00:00Z",
      },
      {
        author: "security",
        content: "Reviewing token scoping and rotation policy.",
        timestamp: "2025-06-02T15:00:00Z",
      },
    ],
    artifact_path: "",
    created_at: "2025-06-02T09:30:00Z",
    updated_at: "2025-06-02T15:00:00Z",
  },
  {
    task_id: "demo-t6",
    title: "Security review: architecture design",
    description: "Review authentication approach, network boundaries, and IAM policies.",
    phase: "ARCHITECTURE",
    status: "backlog",
    assigned_to: "security",
    comments: [],
    artifact_path: "",
    created_at: "2025-06-02T10:00:00Z",
    updated_at: "2025-06-02T10:00:00Z",
  },
  {
    task_id: "demo-t7",
    title: "Design CI/CD pipeline",
    description: "Define build, test, and deployment pipeline using CodePipeline or GitHub Actions.",
    phase: "ARCHITECTURE",
    status: "backlog",
    assigned_to: "sa",
    comments: [],
    artifact_path: "",
    created_at: "2025-06-02T10:00:00Z",
    updated_at: "2025-06-02T10:00:00Z",
  },
  {
    task_id: "demo-t8",
    title: "Define API contracts",
    description: "Create OpenAPI specification for all REST endpoints.",
    phase: "ARCHITECTURE",
    status: "backlog",
    assigned_to: "dev",
    comments: [],
    artifact_path: "",
    created_at: "2025-06-02T10:30:00Z",
    updated_at: "2025-06-02T10:30:00Z",
  },
  {
    task_id: "demo-t9",
    title: "Create test strategy",
    description: "Define testing approach: unit, integration, e2e, and performance testing.",
    phase: "ARCHITECTURE",
    status: "backlog",
    assigned_to: "qa",
    comments: [],
    artifact_path: "",
    created_at: "2025-06-02T10:30:00Z",
    updated_at: "2025-06-02T10:30:00Z",
  },
  // ── POC phase tasks ──────────────────────────────────────────────────
  {
    task_id: "demo-t10",
    title: "Implement auth proof-of-concept",
    description: "Build working Cognito integration with login/signup flow.",
    phase: "POC",
    status: "backlog",
    assigned_to: "dev",
    comments: [],
    artifact_path: "poc/auth-poc.md",
    created_at: "2025-06-03T09:00:00Z",
    updated_at: "2025-06-03T09:00:00Z",
  },
  {
    task_id: "demo-t11",
    title: "Deploy PoC infrastructure",
    description: "Provision VPC, Lambda, DynamoDB, and API Gateway for PoC environment.",
    phase: "POC",
    status: "backlog",
    assigned_to: "infra",
    comments: [],
    artifact_path: "",
    created_at: "2025-06-03T09:00:00Z",
    updated_at: "2025-06-03T09:00:00Z",
  },
  {
    task_id: "demo-t14",
    title: "Build API prototype endpoints",
    description: "Implement core CRUD endpoints against DynamoDB with request validation.",
    phase: "POC",
    status: "backlog",
    assigned_to: "dev",
    comments: [],
    artifact_path: "",
    created_at: "2025-06-03T09:30:00Z",
    updated_at: "2025-06-03T09:30:00Z",
  },
  {
    task_id: "demo-t15",
    title: "Run load test baseline",
    description: "Execute load tests at 2x expected traffic and measure p50/p95/p99 latency.",
    phase: "POC",
    status: "backlog",
    assigned_to: "qa",
    comments: [],
    artifact_path: "poc/load-test-results.md",
    created_at: "2025-06-03T10:00:00Z",
    updated_at: "2025-06-03T10:00:00Z",
  },
  {
    task_id: "demo-t16",
    title: "Security scan PoC environment",
    description: "Run OWASP Top 10 scan and validate Cognito token configuration.",
    phase: "POC",
    status: "backlog",
    assigned_to: "security",
    comments: [],
    artifact_path: "",
    created_at: "2025-06-03T10:00:00Z",
    updated_at: "2025-06-03T10:00:00Z",
  },
  // ── PRODUCTION phase tasks ─────────────────────────────────────────
  {
    task_id: "demo-t12",
    title: "Implement tenant isolation",
    description: "Add row-level security and tenant context propagation across all services.",
    phase: "PRODUCTION",
    status: "backlog",
    assigned_to: "dev",
    comments: [],
    artifact_path: "",
    created_at: "2025-06-10T09:00:00Z",
    updated_at: "2025-06-10T09:00:00Z",
  },
  {
    task_id: "demo-t17",
    title: "Build data migration pipeline",
    description: "Create ETL pipeline to migrate 47 tables from PostgreSQL to DynamoDB.",
    phase: "PRODUCTION",
    status: "backlog",
    assigned_to: "data",
    comments: [],
    artifact_path: "production/migration-report.md",
    created_at: "2025-06-10T09:00:00Z",
    updated_at: "2025-06-10T09:00:00Z",
  },
  {
    task_id: "demo-t18",
    title: "Configure blue-green deployment",
    description: "Set up CodeDeploy with blue-green strategy and automatic rollback triggers.",
    phase: "PRODUCTION",
    status: "backlog",
    assigned_to: "infra",
    comments: [],
    artifact_path: "production/deployment-guide.md",
    created_at: "2025-06-10T09:30:00Z",
    updated_at: "2025-06-10T09:30:00Z",
  },
  {
    task_id: "demo-t19",
    title: "Set up monitoring and alerting",
    description: "Configure CloudWatch dashboards, alarms, and PagerDuty integration.",
    phase: "PRODUCTION",
    status: "backlog",
    assigned_to: "infra",
    comments: [],
    artifact_path: "production/monitoring.md",
    created_at: "2025-06-10T10:00:00Z",
    updated_at: "2025-06-10T10:00:00Z",
  },
  {
    task_id: "demo-t20",
    title: "Production security audit",
    description: "Full penetration test and PCI-DSS compliance validation.",
    phase: "PRODUCTION",
    status: "backlog",
    assigned_to: "security",
    comments: [],
    artifact_path: "",
    created_at: "2025-06-10T10:00:00Z",
    updated_at: "2025-06-10T10:00:00Z",
  },
  {
    task_id: "demo-t21",
    title: "End-to-end regression testing",
    description: "Full regression suite against production environment with synthetic tenants.",
    phase: "PRODUCTION",
    status: "backlog",
    assigned_to: "qa",
    comments: [],
    artifact_path: "",
    created_at: "2025-06-10T10:30:00Z",
    updated_at: "2025-06-10T10:30:00Z",
  },
  // ── HANDOFF phase tasks ────────────────────────────────────────────
  {
    task_id: "demo-t13",
    title: "Write operations runbook",
    description: "Document monitoring, alerting, scaling, and incident response procedures.",
    phase: "HANDOFF",
    status: "backlog",
    assigned_to: "infra",
    comments: [],
    artifact_path: "handoff/operations-runbook.md",
    created_at: "2025-06-17T09:00:00Z",
    updated_at: "2025-06-17T09:00:00Z",
  },
  {
    task_id: "demo-t22",
    title: "Create API documentation",
    description: "Generate OpenAPI docs with examples, error codes, and rate limiting details.",
    phase: "HANDOFF",
    status: "backlog",
    assigned_to: "dev",
    comments: [],
    artifact_path: "handoff/api-docs.md",
    created_at: "2025-06-17T09:00:00Z",
    updated_at: "2025-06-17T09:00:00Z",
  },
  {
    task_id: "demo-t23",
    title: "Prepare training materials",
    description: "Build slide deck and hands-on lab guide for customer DevOps team.",
    phase: "HANDOFF",
    status: "backlog",
    assigned_to: "sa",
    comments: [],
    artifact_path: "handoff/training.md",
    created_at: "2025-06-17T09:30:00Z",
    updated_at: "2025-06-17T09:30:00Z",
  },
  {
    task_id: "demo-t24",
    title: "Final compliance report",
    description: "Compile PCI-DSS evidence package and SOC 2 control mappings.",
    phase: "HANDOFF",
    status: "backlog",
    assigned_to: "security",
    comments: [],
    artifact_path: "handoff/compliance-report.md",
    created_at: "2025-06-17T10:00:00Z",
    updated_at: "2025-06-17T10:00:00Z",
  },
  {
    task_id: "demo-t25",
    title: "Knowledge transfer sessions",
    description: "Run 3 sessions covering architecture, operations, and incident response.",
    phase: "HANDOFF",
    status: "backlog",
    assigned_to: "sa",
    comments: [],
    artifact_path: "",
    created_at: "2025-06-17T10:00:00Z",
    updated_at: "2025-06-17T10:00:00Z",
  },
];

// ---------------------------------------------------------------------------
// Demo data reset (for phase-jump controls)
// ---------------------------------------------------------------------------

const _INITIAL_PROJECT_STATUS: ProjectStatus = structuredClone(DEMO_PROJECT_STATUS);
const _INITIAL_BOARD_TASKS: BoardTask[] = structuredClone(DEMO_BOARD_TASKS);

/** Reset all mutable demo data to factory defaults. */
export function resetDemoData(): void {
  Object.assign(DEMO_PROJECT_STATUS, structuredClone(_INITIAL_PROJECT_STATUS));
  DEMO_BOARD_TASKS.length = 0;
  DEMO_BOARD_TASKS.push(...structuredClone(_INITIAL_BOARD_TASKS));
}

// ---------------------------------------------------------------------------
// M5f: Mock artifact content (markdown previews)
// ---------------------------------------------------------------------------

export const DEMO_ARTIFACT_CONTENT: Record<string, string> = {
  "docs/requirements.md": `# Requirements Document

## Functional Requirements

1. **Multi-tenant SaaS platform** supporting 50+ concurrent tenants
2. **User authentication** via Cognito with role-based access control
3. **REST API** for all CRUD operations with OpenAPI spec
4. **Real-time notifications** via WebSocket for status updates
5. **Document storage** in S3 with tenant isolation

## Non-Functional Requirements

- **Availability**: 99.9% uptime SLA
- **Latency**: API responses < 200ms p95
- **Security**: SOC 2 Type II compliance
- **Scalability**: Auto-scale to 10k requests/minute

## Acceptance Criteria

- All API endpoints documented and tested
- Load test passes at 2x expected traffic
- Security scan shows zero critical/high findings
`,
  "docs/interviews.md": `# Stakeholder Interviews

## Interview 1: VP of Engineering
- Primary concern: **operational overhead** — wants serverless where possible
- Must integrate with existing CI/CD pipeline (GitHub Actions)
- Budget: $5k/month for infrastructure in first year

## Interview 2: Product Manager
- Priority: fast iteration on features
- Needs real-time dashboard for monitoring engagement progress
- Wants approval gates before each phase transition

## Interview 3: Security Lead
- Requires tenant data isolation at all layers
- Encryption at rest and in transit mandatory
- Audit logging for all data access
`,
  "docs/architecture.md": `# System Architecture

## Overview

Serverless-first architecture using AWS managed services to minimize operational overhead.

## Components

### API Layer
- **API Gateway** (REST) with Lambda integrations
- Request validation and rate limiting at gateway level
- Cognito authorizer for JWT-based authentication

### Compute
- **Lambda** for synchronous API handlers (< 30s)
- **ECS Fargate** for long-running agent swarms (up to 1 hour)
- **Step Functions** for phase orchestration with approval gates

### Data
- **DynamoDB** single-table design for operational data
- **S3** for document storage and artifact persistence
- **Bedrock Knowledge Base** for semantic search across project artifacts

### Real-Time
- **API Gateway WebSocket** for live dashboard updates
- Connection management via DynamoDB with TTL cleanup

## Architecture Decision Records
- ADR-001: Serverless over containers for API layer
- ADR-002: Cognito for authentication (vs custom auth)
`,
  "docs/data-model.md": `# Data Model

## DynamoDB Single-Table Design

### Access Patterns

| Pattern | PK | SK |
|---------|----|----|
| Get project | PROJECT#{id} | METADATA |
| List tasks | PROJECT#{id} | TASK#{phase}#{id} |
| Get activity | PROJECT#{id} | EVENT#{timestamp} |

### Global Secondary Indexes

1. **GSI1**: Phase lookup — PK: PHASE#{name}, SK: PROJECT#{id}
2. **GSI2**: Agent lookup — PK: AGENT#{name}, SK: TASK#{id}
3. **GSI3**: Status lookup — PK: STATUS#{status}, SK: timestamp
`,
  "poc/auth-poc.md": `# Auth Proof-of-Concept

## Cognito Configuration
- User Pool: \`ecommerce-migration-poc\`
- App Client: SPA with PKCE flow (no client secret)
- Custom attributes: \`tenant_id\`, \`role\`

## Implemented Flows
1. **Sign Up** — email verification with custom message template
2. **Sign In** — returns JWT with tenant context in custom claims
3. **Token Refresh** — silent refresh via iframe (SPA pattern)
4. **Password Reset** — verification code via SES

## Integration Points
- API Gateway Cognito Authorizer validates JWT on every request
- Lambda extracts \`tenant_id\` from token claims for row-level filtering
- CloudFront signed cookies for S3 asset access

## Test Results
- Sign-up to first API call: **1.2 seconds** (target: < 3s)
- Token refresh latency: **89ms** p95
- Concurrent auth flows tested: **500 simultaneous**
`,
  "poc/load-test-results.md": `# Load Test Results

## Test Configuration
- **Tool**: Artillery.io with custom scenarios
- **Duration**: 10 minutes sustained + 2 minute spike
- **Target**: 2x expected peak (20,000 req/min)
- **Regions**: us-east-1, eu-west-1

## Results Summary

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| p50 latency | < 100ms | 67ms | PASS |
| p95 latency | < 200ms | 142ms | PASS |
| p99 latency | < 500ms | 289ms | PASS |
| Error rate | < 0.1% | 0.02% | PASS |
| Throughput | 20k/min | 23.4k/min | PASS |

## Cold Start Analysis
- Lambda cold starts: 847ms average (provisioned concurrency applied)
- After provisioned concurrency: 12ms average
- Recommendation: Keep 10 provisioned instances for production

## Bottlenecks Identified
1. DynamoDB consumed capacity spikes during burst — switched to on-demand
2. API Gateway throttling at 10k/s default — requested limit increase
`,
  "poc/migration-runbook.md": `# Migration Runbook (Draft)

## Pre-Migration Checklist
- [ ] Database snapshot taken and verified
- [ ] Blue-green deployment tested in staging
- [ ] Rollback procedure validated
- [ ] Customer notification sent (T-48 hours)
- [ ] On-call roster confirmed

## Migration Steps
1. Enable DynamoDB Streams on source table
2. Run initial bulk data load (estimated: 4 hours)
3. Activate CDC replication via Lambda
4. Verify data consistency (checksums)
5. Switch DNS to new API Gateway endpoint
6. Monitor for 30 minutes
7. Disable legacy API endpoints

## Rollback Procedure
- **Trigger**: Error rate > 1% or p95 > 500ms for 5 minutes
- **Action**: Revert DNS to legacy endpoints (TTL: 60s)
- **Recovery**: All writes during migration window captured in DynamoDB Streams
`,
  "production/deployment-guide.md": `# Production Deployment Guide

## Blue-Green Deployment Strategy

### Architecture
- **Blue**: Current production (legacy EC2 + RDS)
- **Green**: New architecture (Lambda + DynamoDB + API Gateway)
- **Router**: Route 53 weighted routing for gradual traffic shift

### Deployment Steps
1. Deploy green environment via Terraform
2. Run smoke tests against green (automated)
3. Shift 5% traffic to green, monitor for 15 minutes
4. Shift 25% → 50% → 100% (15-minute intervals)
5. Decommission blue after 48-hour bake period

### Rollback Triggers (Automatic)
- Error rate exceeds 0.5% over 5-minute window
- p95 latency exceeds 400ms over 5-minute window
- Any 5xx errors from health check endpoints

### CodeDeploy Configuration
\`\`\`yaml
deployment:
  type: BLUE_GREEN
  traffic_routing:
    type: TimeBasedLinear
    interval: 15
    percentage: 25
  alarms:
    - HighErrorRate
    - HighLatency
    - HealthCheckFailed
\`\`\`
`,
  "production/monitoring.md": `# Monitoring & Alerting Configuration

## CloudWatch Dashboards

### API Health Dashboard
- Request count (1-minute granularity)
- Error rate by endpoint
- Latency percentiles (p50, p95, p99)
- Lambda concurrent executions
- DynamoDB consumed capacity

### Infrastructure Dashboard
- VPC flow logs summary
- NAT Gateway throughput
- S3 request metrics
- CloudFront cache hit ratio

## Alarm Configuration

| Alarm | Threshold | Period | Action |
|-------|-----------|--------|--------|
| High Error Rate | > 1% | 5 min | PagerDuty P1 |
| High Latency | p95 > 300ms | 5 min | PagerDuty P2 |
| DynamoDB Throttling | > 0 | 1 min | Slack + Auto-scale |
| Lambda Errors | > 10/min | 5 min | PagerDuty P2 |
| Budget Alert | > 80% forecast | Daily | Email to stakeholders |

## Log Aggregation
- All Lambda logs → CloudWatch Log Groups
- Structured JSON logging with correlation IDs
- 30-day retention, archived to S3 Glacier after 90 days
`,
  "production/migration-report.md": `# Data Migration Report

## Summary
- **Tables migrated**: 47 of 47 (100%)
- **Records migrated**: 2,847,329
- **Duration**: 3 hours 42 minutes
- **Data loss**: 0 records
- **Schema mismatches resolved**: 12 (see details below)

## Schema Adaptations
| Table | Issue | Resolution |
|-------|-------|-----------|
| orders | DATE column nulls | Default to epoch, flagged for review |
| products | VARCHAR(MAX) fields | Truncated to 400KB DynamoDB limit |
| users | Duplicate emails | Merged by most recent login timestamp |

## Validation Results
- Checksum verification: PASS (all 47 tables)
- Record count verification: PASS
- Sample query validation: 50 random queries, all returned identical results
- Referential integrity: PASS (all foreign key relationships preserved as GSI lookups)

## Performance Impact
- Source database load during migration: < 15% CPU increase
- Zero downtime — CDC replication maintained consistency
`,
  "handoff/operations-runbook.md": `# Operations Runbook

## Incident Response

### P1 — Service Down
1. Check CloudWatch API Health dashboard
2. Verify Lambda function health: \`aws lambda get-function --function-name api-handler\`
3. Check DynamoDB table status and throttling metrics
4. If Lambda errors: check recent deployment, rollback if needed
5. If DynamoDB throttling: verify on-demand scaling is active
6. Escalation: page Solutions Architect if not resolved in 15 minutes

### P2 — Degraded Performance
1. Check latency dashboard for affected endpoints
2. Review Lambda cold start metrics
3. Verify provisioned concurrency allocation
4. Check downstream service health (Cognito, S3)

## Scaling Procedures
- **Lambda**: Auto-scales. Monitor concurrent execution limit (1000 default)
- **DynamoDB**: On-demand mode, no action needed for normal scaling
- **API Gateway**: Request throttle increase via AWS Support if approaching 10k/s

## Routine Maintenance
- **Weekly**: Review CloudWatch cost anomaly report
- **Monthly**: Rotate Cognito signing keys, review IAM access reports
- **Quarterly**: Run penetration test, update dependency versions
`,
  "handoff/api-docs.md": `# API Documentation

## Base URL
\`https://api.ecommerce-platform.example.com/v1\`

## Authentication
All endpoints require a valid JWT from Cognito in the Authorization header:
\`\`\`
Authorization: Bearer <id_token>
\`\`\`

## Endpoints

### Tenants
| Method | Path | Description |
|--------|------|-------------|
| GET | /tenants/{id} | Get tenant details |
| PUT | /tenants/{id} | Update tenant settings |

### Products
| Method | Path | Description |
|--------|------|-------------|
| GET | /products | List products (paginated) |
| POST | /products | Create product |
| GET | /products/{id} | Get product details |
| PUT | /products/{id} | Update product |
| DELETE | /products/{id} | Soft-delete product |

### Orders
| Method | Path | Description |
|--------|------|-------------|
| GET | /orders | List orders (paginated, filtered by tenant) |
| POST | /orders | Create order |
| GET | /orders/{id} | Get order with line items |
| PATCH | /orders/{id}/status | Update order status |

## Error Codes
| Code | Meaning |
|------|---------|
| 400 | Validation error (see \`errors\` array in response) |
| 401 | Missing or expired JWT token |
| 403 | Tenant isolation violation |
| 404 | Resource not found |
| 429 | Rate limit exceeded (retry after header included) |
`,
  "handoff/training.md": `# Training Materials

## Session 1: Architecture Overview (2 hours)

### Topics
- System architecture walkthrough (API Gateway → Lambda → DynamoDB)
- Multi-tenancy implementation and data isolation
- Authentication flow with Cognito
- Infrastructure-as-Code with Terraform

### Hands-On Lab
- Deploy a staging environment from scratch using Terraform
- Modify a Lambda function and deploy via CI/CD pipeline
- Verify tenant isolation with test accounts

## Session 2: Operations & Monitoring (2 hours)

### Topics
- CloudWatch dashboards and alarm configuration
- Incident response procedures (P1/P2 runbooks)
- Log aggregation and structured logging
- Cost management and budget alerts

### Hands-On Lab
- Simulate a P2 incident and follow the runbook
- Create a custom CloudWatch alarm
- Generate a cost report for the current month

## Session 3: Security & Compliance (1.5 hours)

### Topics
- PCI-DSS controls and evidence locations
- IAM policy structure and least-privilege principles
- Encryption at rest (KMS) and in transit (TLS 1.3)
- Audit logging and compliance reporting

### Hands-On Lab
- Run a security scan with AWS Inspector
- Review IAM Access Analyzer findings
- Generate a compliance evidence package
`,
  "handoff/compliance-report.md": `# PCI-DSS Compliance Report

## Assessment Summary
- **Scope**: E-Commerce Platform (AWS serverless architecture)
- **Assessment Date**: Week of go-live
- **Result**: All applicable controls satisfied

## Control Mapping

### Requirement 1: Network Security
- VPC with private subnets for all compute resources
- Security groups follow least-privilege (no 0.0.0.0/0 ingress)
- VPC Flow Logs enabled and retained for 90 days

### Requirement 3: Protect Stored Data
- DynamoDB encryption at rest via AWS-managed KMS key
- S3 bucket encryption (AES-256) with bucket policy enforcement
- No cardholder data stored in logs (PII redaction Lambda layer)

### Requirement 6: Secure Development
- All code reviewed via PR process before merge
- Automated SAST scanning in CI pipeline
- Dependency vulnerability scanning (Dependabot + Snyk)

### Requirement 7: Access Control
- Cognito user pools with MFA enforced for admin roles
- IAM roles follow least-privilege principle
- No long-lived access keys — STS temporary credentials only

### Requirement 10: Logging & Monitoring
- CloudTrail enabled for all API activity
- CloudWatch Logs with 90-day retention
- Automated alerting for suspicious access patterns

## Evidence Package
All evidence artifacts stored in S3 bucket \`compliance-evidence-{account-id}\`
with versioning enabled and cross-region replication.
`,
  "docs/phase-summaries/architecture.md": `# Architecture Phase Summary

## Overview
The Architecture phase established the foundational design for a serverless, multi-tenant SaaS platform on AWS, prioritizing operational efficiency and scalability.

## What We Accomplished

### 1. System Architecture Design
- Designed serverless-first architecture using API Gateway, Lambda, DynamoDB, and S3
- Established multi-tenant isolation patterns at database and storage layers
- Created high-availability design with cross-region failover capabilities
- Documented all architectural decisions with trade-off analysis

### 2. Technology Selection
- **Compute**: Lambda for API and async workloads (no operational overhead)
- **Data**: DynamoDB for operational data, S3 for artifacts
- **Authentication**: Cognito user pools with MFA support
- **Monitoring**: CloudWatch Logs + X-Ray for distributed tracing
- **Infrastructure**: Terraform for IaC, GitHub Actions for CI/CD

### 3. API Contract Definition
- RESTful API with OpenAPI 3.0 specification
- 25+ endpoints covering authentication, data management, and webhooks
- Request/response schemas validated against specification
- Rate limiting and retry policies documented

## Key Decisions & Rationale

| Decision | Rationale | Alternative Considered |
|----------|-----------|------------------------|
| Serverless over containers | Zero operational overhead, scales automatically to 0 in off-hours | ECS Fargate (higher baseline cost) |
| Single-tenant DynamoDB tables | Simplifies data isolation and compliance auditing | Multi-tenant with row-level security |
| API Gateway caching | Reduces DynamoDB calls for read-heavy endpoints by 60% | Direct Lambda-to-DynamoDB calls |
| S3 + CloudFront | Cost-effective content delivery with global footprint | Application-managed CDN |

## Deliverables

1. ✅ **System Architecture Document** - 15 pages, 20+ diagrams
2. ✅ **API Contracts** - OpenAPI specification for all endpoints
3. ✅ **Data Models** - DynamoDB schemas with GSI strategy
4. ✅ **Security Architecture** - Encryption, IAM policies, network isolation
5. ✅ **Cost Model** - Projected spend by service with scaling scenarios
6. ✅ **Deployment Topology** - VPC layout, subnet strategy, cross-region setup

## Next Steps
The team is ready to proceed to the Proof of Concept phase to validate these architectural decisions through implementation and load testing.
`,
  "docs/phase-summaries/poc.md": `# Proof of Concept Phase Summary

## Overview
The PoC phase successfully validated core architectural components through working code and demonstrated end-to-end functionality, confirming the viability of the proposed design.

## What We Accomplished

### 1. Core API Implementation
- Implemented 8 critical API endpoints covering authentication, user management, and data retrieval
- Lambda functions tested and deployed to AWS
- API Gateway integrations working with proper request/response validation
- Performance verified: API responses averaging 120ms (well below 200ms SLA)

### 2. Multi-Tenant Data Model
- DynamoDB tables provisioned with proper partition key strategy
- Tenant isolation verified through integration tests
- Query performance tested at scale (1M+ items)
- Global Secondary Indexes performing efficiently

### 3. Authentication & Authorization
- Cognito integration complete with user pool configuration
- Custom authorizer Lambda validating JWT tokens
- Role-based access control (RBAC) implemented and tested
- MFA setup validated for admin accounts

### 4. Infrastructure & Deployment
- Terraform modules created for all AWS resources
- GitHub Actions pipeline deploying changes to dev environment
- Infrastructure-as-Code versioned and reviewed
- Automated testing integrated into deployment pipeline

## Key Decisions & Rationale

| Decision | Rationale |
|----------|-----------|
| Lambda for all compute | Simplified deployment, automatic scaling, reduced operational burden |
| DynamoDB on-demand pricing | Cost-effective for variable load during PoC phase |
| Single region deployment | Simplified validation; multi-region added in Production phase |
| GitHub Actions for CI/CD | Integrated with existing workflow, fast iteration |

## Deliverables

1. ✅ **Working API** - All endpoints deployed and tested
2. ✅ **Terraform Modules** - Reusable infrastructure code
3. ✅ **Automated Tests** - 45+ integration tests, 92% code coverage
4. ✅ **Load Test Report** - Verified performance under 2x expected load
5. ✅ **Security Scan Report** - Zero critical/high findings
6. ✅ **Runbooks** - Deployment and incident response procedures

## Validation Results

- ✅ API latency meets SLA targets
- ✅ Multi-tenant isolation confirmed via integration tests
- ✅ Infrastructure cost within budget ($2.3k/month projected)
- ✅ All security requirements satisfied

## Next Steps
Proceed to Production phase for hardening, monitoring setup, and multi-region deployment.
`,
  "docs/phase-summaries/production.md": `# Production Phase Summary

## Overview
The Production phase hardened the system, implemented comprehensive monitoring, enabled multi-region failover, and prepared the platform for customer launch.

## What We Accomplished

### 1. System Hardening
- Added DynamoDB backup and point-in-time recovery
- Enabled CloudTrail for audit logging
- Implemented VPC Flow Logs for network monitoring
- Configured WAF rules on API Gateway
- Enabled S3 versioning and cross-region replication

### 2. Monitoring & Observability
- CloudWatch dashboards for operations team
- Automated alerts for SLA violations (latency, error rates)
- X-Ray tracing for distributed transaction visibility
- Custom metrics for business KPIs (sign-ups, API calls, tenant activity)
- Log aggregation with structured logging format

### 3. Multi-Region Deployment
- Secondary region (eu-west-1) configured as active-active
- Route 53 health checks for automatic failover
- DynamoDB Global Tables enabled for replication
- S3 Cross-Region Replication configured
- DNS failover tested and verified

### 4. Performance Optimization
- API response times optimized: avg 85ms, p99 <200ms
- DynamoDB queries tuned through GSI strategy
- Lambda provisioned concurrency for critical endpoints
- CloudFront caching configured for S3 content

## Key Decisions & Rationale

| Decision | Rationale |
|----------|-----------|
| Active-active multi-region | True resilience; RTO/RPO measured in seconds |
| DynamoDB provisioned capacity (prod) | Predictable costs, guaranteed performance |
| CloudWatch + X-Ray | Vendor-agnostic observability, SOC 2 compliant |
| WAF at API Gateway | Protection without additional infrastructure |

## Deliverables

1. ✅ **Production Deployment** - Multi-region active-active setup
2. ✅ **Monitoring & Alerting** - 50+ dashboards and alert policies
3. ✅ **Disaster Recovery Plan** - RTO: 5 minutes, RPO: 1 minute
4. ✅ **Security Hardening Report** - All OWASP Top 10 mitigated
5. ✅ **Runbooks** - Incident response procedures for operations team
6. ✅ **Capacity Planning** - Cost projections for 12-month horizon
7. ✅ **Compliance Evidence** - SOC 2 audit ready

## Performance Metrics

- **Uptime**: 99.95% in first month
- **API Latency**: p50: 45ms, p95: 120ms, p99: 195ms
- **Error Rate**: 0.02% (well below 0.1% SLA)
- **Cost**: $3.8k/month (within budget)
- **Scaling**: Successfully handled 1.5x peak load

## Next Steps
Proceed to Handoff phase for customer training and operational transition to customer's DevOps team.
`,
  "docs/phase-summaries/handoff.md": `# Handoff Phase Summary

## Overview
The Handoff phase transferred operational responsibility to the customer's team through comprehensive training, documentation, and operational readiness validation.

## What We Accomplished

### 1. Documentation Delivery
- Complete System Architecture guide with runbooks
- Operations manual with troubleshooting procedures
- API documentation with SDKs and code examples
- Infrastructure-as-Code repository transferred to customer
- Security and compliance documentation package

### 2. Operations Team Training
- 3-day hands-on training for DevOps and SRE team
- Session 1: Architecture overview and system components
- Session 2: Deployment, scaling, and infrastructure management
- Session 3: Monitoring, alerting, and incident response
- Training materials provided (videos, slide decks, labs)

### 3. Runbooks & Procedures
- Common operational tasks (deployments, rollbacks, updates)
- Incident response procedures for critical scenarios
- Monitoring and alerting configuration guide
- Backup and disaster recovery procedures
- Performance tuning and optimization guide

### 4. Operational Readiness
- Customer's team performed 50+ manual scenarios
- Simulated failures (region outage, database failure) with successful recovery
- Escalation procedures tested and validated
- On-call rotation established with escalation chain
- Change management process documented and agreed

## Knowledge Transfer Results

| Area | Coverage | Status |
|------|----------|--------|
| System Architecture | 100% | ✅ Complete |
| Deployment & Infrastructure | 100% | ✅ Complete |
| Monitoring & Alerting | 95% | ✅ Complete |
| Incident Response | 90% | ✅ Complete |
| Cost Optimization | 85% | ✅ Complete |

## Deliverables

1. ✅ **Architecture Documentation** - Complete system overview with diagrams
2. ✅ **Operations Manual** - 200+ pages of procedures and troubleshooting
3. ✅ **Training Materials** - Videos, labs, and reference guides
4. ✅ **Runbooks** - Automated and manual procedures for all scenarios
5. ✅ **Code Repository** - Source and infrastructure-as-code with CI/CD
6. ✅ **Monitoring Setup** - Dashboards and alerts configured in customer's AWS account
7. ✅ **Support Agreement** - 30-day extended support with escalation procedures

## Post-Launch Support

- Customer's team confident and capable of operating the system independently
- All critical personnel trained and certified
- Escalation contacts established for complex issues
- Weekly check-ins scheduled for first 30 days post-launch

## Project Completion

The platform is now fully operational under customer control:
- ✅ All deliverables accepted by customer
- ✅ Compliance and security requirements satisfied
- ✅ Performance targets met across all regions
- ✅ Cost within budget and projections
- ✅ Operations team ready for independent operation

**Project Status: COMPLETE AND HANDED OFF** 🎉
`,
};

/** Get mock markdown content for an artifact, or a placeholder for unknown paths. */
export function getArtifactContent(gitPath: string): string {
  return (
    DEMO_ARTIFACT_CONTENT[gitPath] ??
    `# ${gitPath.split("/").pop()}\n\n*Content preview available in live mode.*`
  );
}

// ---------------------------------------------------------------------------
// M5f: Approval helpers (mutate demo state locally)
// ---------------------------------------------------------------------------

/** Advance the demo project to the next phase. Returns the new phase. */
export function advanceDemoPhase(): Phase {
  const current = DEMO_PROJECT_STATUS.current_phase;
  const idx = PHASE_ORDER.indexOf(current);
  const next = idx < PHASE_ORDER.length - 1 ? PHASE_ORDER[idx + 1] : current;
  DEMO_PROJECT_STATUS.current_phase = next;
  DEMO_PROJECT_STATUS.phase_status = "IN_PROGRESS";
  DEMO_PROJECT_STATUS.updated_at = new Date().toISOString();
  return next;
}

/** Set the demo project to AWAITING_APPROVAL status. */
export function setDemoAwaitingApproval(): void {
  DEMO_PROJECT_STATUS.phase_status = "AWAITING_APPROVAL";
  DEMO_PROJECT_STATUS.updated_at = new Date().toISOString();
}

/** Set the demo project to AWAITING_INPUT (interrupt pending). */
export function setDemoAwaitingInput(): void {
  DEMO_PROJECT_STATUS.phase_status = "AWAITING_INPUT";
  DEMO_PROJECT_STATUS.updated_at = new Date().toISOString();
}

/** Clear AWAITING_INPUT back to IN_PROGRESS (interrupt answered). */
export function clearDemoAwaitingInput(): void {
  if (DEMO_PROJECT_STATUS.phase_status === "AWAITING_INPUT") {
    DEMO_PROJECT_STATUS.phase_status = "IN_PROGRESS";
    DEMO_PROJECT_STATUS.updated_at = new Date().toISOString();
  }
}

/** Clear AWAITING_APPROVAL back to IN_PROGRESS (revision requested). */
export function clearDemoAwaitingApproval(): void {
  if (DEMO_PROJECT_STATUS.phase_status === "AWAITING_APPROVAL") {
    DEMO_PROJECT_STATUS.phase_status = "IN_PROGRESS";
    DEMO_PROJECT_STATUS.updated_at = new Date().toISOString();
  }
}

/** Mutate a demo board task in place (for task_updated events). */
export function updateDemoBoardTask(
  taskId: string,
  updates: TaskUpdateFields,
): void {
  const task = DEMO_BOARD_TASKS.find((t) => t.task_id === taskId);
  if (!task) return;
  if (updates.status) {
    task.status = updates.status;
    task.updated_at = new Date().toISOString();
  }
  if (updates.assigned_to) {
    task.assigned_to = updates.assigned_to;
  }
}

/** Add or update a demo deliverable. If a deliverable with the same git_path
 *  already exists in the phase, update it (version bump); otherwise append. */
export function addDemoDeliverable(phase: string, item: DeliverableItem): void {
  if (!DEMO_PROJECT_STATUS.deliverables[phase]) {
    DEMO_PROJECT_STATUS.deliverables[phase] = [];
  }
  const existing = DEMO_PROJECT_STATUS.deliverables[phase].find(
    (d) => d.git_path === item.git_path,
  );
  if (existing) {
    existing.version = item.version;
    existing.created_at = item.created_at;
  } else {
    DEMO_PROJECT_STATUS.deliverables[phase].push(item);
  }
}

// ---------------------------------------------------------------------------
// M5f: Mock interrupt
// ---------------------------------------------------------------------------

export const DEMO_APPROVAL = {
  question:
    "The **Architecture** phase is complete. All deliverables have been drafted and reviewed by the team. Please review the artifacts and let us know if you'd like to approve and move to the next phase, or if you have feedback.",
  quickReplies: [
    "Approve — looks good, continue to the next phase.",
    "I have some feedback before we proceed.",
  ],
} as const;

export const DEMO_INTERRUPT = {
  interrupt_id: "demo-int-1",
  question:
    "The architecture uses a single DynamoDB table. Should we add a dedicated search index (OpenSearch) for full-text search, or is DynamoDB + GSIs sufficient for the MVP?",
  phase: "ARCHITECTURE",
  quickReplies: [
    "DynamoDB + GSIs is sufficient for the MVP. We can add OpenSearch later if search requirements grow.",
    "Add OpenSearch now. Full-text search is a core requirement and retrofitting will be harder later.",
    "Let's start with DynamoDB GSIs but design the data layer so OpenSearch can be added without major refactoring.",
  ],
} as const;

// ---------------------------------------------------------------------------
// Mock chat history (shown on first load)
// ---------------------------------------------------------------------------

export const DEMO_CHAT_HISTORY: ChatMessage[] = [
  {
    message_id: "demo-welcome",
    role: "pm",
    content:
      "Welcome to CloudCrew! I'm your Project Manager. I can help you plan architecture, track progress, and answer questions about your engagement.\n\nThis is a demo environment — feel free to send messages and I'll respond with simulated replies so you can explore the interface.",
    timestamp: new Date(Date.now() - 60_000).toISOString(),
  },
];

// ---------------------------------------------------------------------------
// Simulated PM responses
// ---------------------------------------------------------------------------

const PM_RESPONSES: Record<string, string> = {
  hello:
    "Hello! Great to have you here. How can I help with your project today? I can walk you through the current architecture decisions, review progress on deliverables, or discuss any concerns you might have.",
  help: "Here's what I can help you with:\n\n- **Project Status** — Check the Dashboard tab for an overview of current phase progress and live agent activity\n- **Architecture Review** — I can explain the technical decisions made so far\n- **Task Tracking** — Visit the Board tab to see tasks organized by status\n- **File Uploads** — Use the attach button below to share documents\n- **Artifacts** — Browse deliverables in the Artifacts tab\n\nJust ask me anything and I'll do my best to assist!",
  status:
    "Here's where we stand:\n\n**Current Phase:** Architecture (Phase 2 of 5)\n**Status:** In Progress\n\nThe Discovery phase completed successfully. We gathered all requirements and stakeholder input. Now the architecture team is designing the system — the Solutions Architect and Data Engineer are collaborating on the infrastructure and data model.\n\nTwo deliverables are in progress:\n1. System Architecture document\n2. Data Model specification\n\nNo blockers at the moment. Would you like more detail on any of these?",
  architecture:
    "The architecture team has decided on a **serverless-first approach** using AWS services:\n\n- **API Layer:** API Gateway + Lambda functions\n- **Data Store:** DynamoDB for operational data, S3 for document storage\n- **Auth:** Cognito user pools with JWT tokens\n- **Real-time:** WebSocket API for live updates\n- **Infrastructure:** Terraform for IaC, deployed via CI/CD pipeline\n\nThis gives us low operational overhead and pay-per-use pricing. The Solutions Architect can walk through the detailed diagrams if you'd like to review them.",
};

const FALLBACK_RESPONSES = [
  "That's a great question. Let me look into that and get back to you with a detailed answer. In a live environment, I'd consult the project knowledge base and coordinate with the specialist agents to give you the most accurate response.",
  "Thanks for bringing that up. I've noted this down. In the full CloudCrew experience, I'd loop in the relevant specialist — whether that's the Solutions Architect, Developer, or Infrastructure Engineer — to address this properly.",
  "Understood. I'll make sure this is tracked as part of our engagement. Is there anything else you'd like to discuss about the project?",
  "Good point. Let me factor that into our planning. The team is making solid progress on the current phase, and your input helps us stay aligned with your expectations.",
  "I appreciate the feedback. In a production engagement, this would be captured in the task ledger and the relevant agents would be notified. Would you like to explore any other features of the dashboard?",
];

function pickResponse(message: string): string {
  const lower = message.toLowerCase().trim();

  for (const [keyword, response] of Object.entries(PM_RESPONSES)) {
    if (lower.includes(keyword)) return response;
  }

  // Deterministic-ish fallback based on message length
  return FALLBACK_RESPONSES[message.length % FALLBACK_RESPONSES.length];
}

// ---------------------------------------------------------------------------
// Streaming simulator — fires events through addEvent (same as WebSocket)
// ---------------------------------------------------------------------------

/**
 * Simulates token-by-token PM response streaming via events.
 *
 * Fires chat_thinking → chat_chunk × N → chat_done events through the
 * provided `addEvent` callback — the exact same path real WebSocket events
 * take. This means swapping the demo for a real backend changes nothing.
 */
export function simulatePmResponse(
  message: string,
  addEvent: (event: WebSocketEvent) => void,
): void {
  const response = pickResponse(message);
  const messageId = `demo-${crypto.randomUUID()}`;
  const phase = DEMO_PROJECT_STATUS.current_phase;

  // Chunk the response into small pieces for realistic streaming
  const chunks = chunkText(response);
  let chunkIndex = 0;

  // Step 1: Fire thinking event
  addEvent({
    event: "chat_thinking",
    project_id: "demo",
    phase,
  });

  // Step 2: After a "thinking" delay, start streaming chunks
  const thinkingDelay = 800 + Math.random() * 700; // 800-1500ms

  setTimeout(() => {
    const interval = setInterval(() => {
      if (chunkIndex < chunks.length) {
        addEvent({
          event: "chat_chunk",
          project_id: "demo",
          phase,
          content: chunks[chunkIndex],
        });
        chunkIndex++;
      } else {
        // Step 3: Done streaming — finalize
        clearInterval(interval);
        addEvent({
          event: "chat_done",
          project_id: "demo",
          phase,
          message_id: messageId,
        });
      }
    }, 20 + Math.random() * 30); // 20-50ms per chunk (simulates token speed)
  }, thinkingDelay);
}

/** Split text into small chunks that look like token streaming. */
export function chunkText(text: string): string[] {
  const chunks: string[] = [];
  let i = 0;
  while (i < text.length) {
    // 2-3 character chunks with consistent timing for natural LLM-like streaming
    const size = 2 + Math.floor(Math.random() * 2);
    chunks.push(text.slice(i, i + size));
    i += size;
  }
  return chunks;
}
