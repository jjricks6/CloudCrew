/**
 * Demo mode — simulates backend behavior so the dashboard works without
 * deployed infrastructure.  Activated when the projectId is "demo".
 */

import type { AgentActivity, BoardTask, ChatMessage, Phase, ProjectStatus } from "./types";

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
  decisions: [
    {
      description: "Use serverless architecture with API Gateway + Lambda",
      rationale: "Lower operational overhead, pay-per-use pricing",
      made_by: "Solutions Architect",
      timestamp: "2025-06-02T14:00:00Z",
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
// Mock active agents (shown on dashboard in demo mode)
// ---------------------------------------------------------------------------

export const DEMO_AGENTS: AgentActivity[] = [
  {
    agent_name: "Solutions Architect",
    status: "active",
    phase: "ARCHITECTURE",
    detail: "Designing system architecture with serverless-first approach",
    timestamp: Date.now() - 30_000,
  },
  {
    agent_name: "Data Engineer",
    status: "active",
    phase: "ARCHITECTURE",
    detail: "Creating DynamoDB single-table design with 3 GSIs",
    timestamp: Date.now() - 45_000,
  },
  {
    agent_name: "Security Engineer",
    status: "idle",
    phase: "ARCHITECTURE",
    detail: "Waiting for VPC design to begin security review",
    timestamp: Date.now() - 120_000,
  },
  {
    agent_name: "Project Manager",
    status: "active",
    phase: "ARCHITECTURE",
    detail: "Coordinating architecture phase deliverables",
    timestamp: Date.now() - 10_000,
  },
];

// ---------------------------------------------------------------------------
// Recent activity derived from task comments (shown on dashboard)
// ---------------------------------------------------------------------------

export interface DemoActivityItem {
  agent: string;
  action: string;
  timestamp: string;
}

/** Build a recent-activity feed from the demo board task comments. */
export function getDemoRecentActivity(): DemoActivityItem[] {
  const items: DemoActivityItem[] = [];
  for (const task of DEMO_BOARD_TASKS) {
    for (const comment of task.comments) {
      items.push({
        agent: comment.author,
        action: comment.content,
        timestamp: comment.timestamp,
      });
    }
    // Also show task status transitions for non-backlog tasks
    if (task.status !== "backlog") {
      items.push({
        agent: task.assigned_to,
        action: `Moved "${task.title}" to ${task.status}`,
        timestamp: task.updated_at,
      });
    }
  }
  // Sort newest first, take top 8
  return items
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, 8);
}

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
  help: "Here's what I can help you with:\n\n- **Project Status** — Check the Dashboard tab for an overview of current phase progress\n- **Architecture Review** — I can explain the technical decisions made so far\n- **Task Tracking** — Visit the Board tab to see tasks organized by status\n- **File Uploads** — Use the attach button below to share documents\n- **Agent Activity** — The Swarm tab shows real-time agent activity\n\nJust ask me anything and I'll do my best to assist!",
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
// Streaming simulator — drives the chatStore exactly like WebSocket would
// ---------------------------------------------------------------------------

/**
 * Simulates token-by-token PM response streaming.
 *
 * 1. Sets isThinking = true (shows thinking indicator)
 * 2. After a delay, starts appending chunks to streamingContent
 * 3. When done, finalizes the stream into a complete message
 *
 * Uses the same chatStore methods that the real WebSocket handler calls.
 */
export function simulatePmResponse(
  message: string,
  chatStore: {
    setThinking: (v: boolean) => void;
    appendChunk: (content: string) => void;
    finalizeStream: (messageId: string) => void;
  },
): void {
  const response = pickResponse(message);
  const messageId = `demo-${crypto.randomUUID()}`;

  // Chunk the response into small pieces for realistic streaming
  const chunks = chunkText(response);
  let chunkIndex = 0;

  // Step 1: Show thinking indicator
  chatStore.setThinking(true);

  // Step 2: After a "thinking" delay, start streaming chunks
  const thinkingDelay = 800 + Math.random() * 700; // 800-1500ms

  setTimeout(() => {
    const interval = setInterval(() => {
      if (chunkIndex < chunks.length) {
        chatStore.appendChunk(chunks[chunkIndex]);
        chunkIndex++;
      } else {
        // Step 3: Done streaming — finalize
        clearInterval(interval);
        chatStore.finalizeStream(messageId);
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
