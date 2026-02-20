/**
 * Demo mode — simulates backend behavior so the dashboard works without
 * deployed infrastructure.  Activated when the projectId is "demo".
 */

import type { ChatMessage, Phase, ProjectStatus } from "./types";

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
