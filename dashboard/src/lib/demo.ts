/**
 * Demo mode — simulates backend behavior so the dashboard works without
 * deployed infrastructure.  Activated when the projectId is "demo".
 */

import type { BoardTask, ChatMessage, Phase, ProjectStatus, TaskUpdateFields, WebSocketEvent } from "./types";
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
  project_name: "CloudCrew Demo",
  current_phase: "ARCHITECTURE" as Phase,
  phase_status: "IN_PROGRESS",
  deliverables: {
    DISCOVERY: [
      {
        name: "Requirements Document",
        git_path: "docs/requirements.md",
        status: "COMPLETE",
      },
      {
        name: "Stakeholder Interviews",
        git_path: "docs/interviews.md",
        status: "COMPLETE",
      },
    ],
    ARCHITECTURE: [
      {
        name: "System Architecture",
        git_path: "docs/architecture.md",
        status: "IN_PROGRESS",
      },
      {
        name: "Data Model",
        git_path: "docs/data-model.md",
        status: "IN_PROGRESS",
      },
    ],
  },
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
    title: "Security review: VPC design",
    description: "Review network architecture for security compliance.",
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
    assigned_to: "infra",
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
  // POC phase tasks (future — will populate when demo reaches POC)
  {
    task_id: "demo-t10",
    title: "Implement auth proof-of-concept",
    description: "Build working Cognito integration with login/signup flow.",
    phase: "POC",
    status: "backlog",
    assigned_to: "dev",
    comments: [],
    artifact_path: "",
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
  // PRODUCTION phase tasks
  {
    task_id: "demo-t12",
    title: "Implement tenant isolation",
    description: "Add row-level security and tenant context propagation across all services.",
    phase: "PRODUCTION",
    status: "backlog",
    assigned_to: "dev",
    comments: [],
    artifact_path: "",
    created_at: "2025-06-04T09:00:00Z",
    updated_at: "2025-06-04T09:00:00Z",
  },
  // HANDOFF phase tasks
  {
    task_id: "demo-t13",
    title: "Write operations runbook",
    description: "Document monitoring, alerting, scaling, and incident response procedures.",
    phase: "HANDOFF",
    status: "backlog",
    assigned_to: "infra",
    comments: [],
    artifact_path: "",
    created_at: "2025-06-05T09:00:00Z",
    updated_at: "2025-06-05T09:00:00Z",
  },
];

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
function chunkText(text: string): string[] {
  const chunks: string[] = [];
  let i = 0;
  while (i < text.length) {
    // Variable chunk size: 1-6 characters
    const size = 1 + Math.floor(Math.random() * 5);
    chunks.push(text.slice(i, i + size));
    i += size;
  }
  return chunks;
}
