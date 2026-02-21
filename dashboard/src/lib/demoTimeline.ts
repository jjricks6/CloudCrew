/**
 * Pure data: scripted event sequences for the demo engine.
 *
 * Each segment is an array of { delayMs, event } steps. The engine plays
 * them sequentially with cumulative delays. Editing the demo means editing
 * this file — the engine (`useDemoEngine.ts`) is a generic scheduler.
 *
 * All events match the WebSocketEvent union so they flow through
 * `agentStore.addEvent()` identically to real backend events.
 */

import type { WebSocketEvent } from "./types";

export interface TimelineStep {
  delayMs: number;
  event: WebSocketEvent;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function active(agent: string, detail: string, delayMs = 0): TimelineStep {
  return {
    delayMs,
    event: {
      event: "agent_active",
      project_id: "demo",
      phase: "ARCHITECTURE",
      agent_name: agent,
      detail,
    },
  };
}

function idle(agent: string, detail: string, delayMs = 0): TimelineStep {
  return {
    delayMs,
    event: {
      event: "agent_idle",
      project_id: "demo",
      phase: "ARCHITECTURE",
      agent_name: agent,
      detail,
    },
  };
}

function handoff(
  from: string,
  to: string,
  delayMs = 200,
): TimelineStep {
  return {
    delayMs,
    event: {
      event: "handoff",
      project_id: "demo",
      phase: "ARCHITECTURE",
      agent_name: to,
      detail: `Handoff from ${from} to ${to}`,
    },
  };
}

function taskUpdate(
  taskId: string,
  updates: Record<string, unknown>,
  delayMs = 0,
): TimelineStep {
  return {
    delayMs,
    event: {
      event: "task_updated",
      project_id: "demo",
      phase: "ARCHITECTURE",
      task_id: taskId,
      updates,
    },
  };
}

// ---------------------------------------------------------------------------
// SEED — initial agents appear (runs once on mount)
// ---------------------------------------------------------------------------

export const SEED_SEGMENT: TimelineStep[] = [];

// ---------------------------------------------------------------------------
// WORK_LOOP — repeating swarm collaboration cycle (~82s)
//
// Event ordering for each transition:
//   1. agent_idle   (source finishes)
//   2. handoff      (arc fires 200ms later)
//   3. agent_active (destination starts 500ms later)
// ---------------------------------------------------------------------------

export const WORK_LOOP_SEGMENT: TimelineStep[] = [
  // ── SA kicks off architecture design ────────────────────────────────
  active("Solutions Architect", "Designing API Gateway integration patterns", 0),

  // ── SA finishes → handoff → Infrastructure ──────────────────────────
  idle("Solutions Architect", "API Gateway design complete", 8000),
  handoff("Solutions Architect", "Infrastructure"),
  active("Infrastructure", "Provisioning VPC subnets and security groups", 500),

  // ── Infrastructure does a SECOND task (no handoff — same agent) ─────
  active("Infrastructure", "Configuring NAT gateways and route tables", 8000),
  // Move a board task to in_progress
  taskUpdate("demo-t7", { status: "in_progress" }, 500),

  // ── Infrastructure finishes → handoff → Security ────────────────────
  idle("Infrastructure", "VPC and routing provisioned", 8000),
  handoff("Infrastructure", "Security Engineer"),
  active("Security Engineer", "Reviewing network ACL and IAM policies", 500),
  // Move security review task to in_progress
  taskUpdate("demo-t6", { status: "in_progress" }, 500),

  // ── Security finishes → handoff → Infrastructure ────────────────────
  idle("Security Engineer", "Security review passed — no critical findings", 10000),
  // Move security review task to review
  taskUpdate("demo-t6", { status: "review" }, 0),
  handoff("Security Engineer", "Infrastructure"),
  active("Infrastructure", "Applying security-recommended NACL rules", 500),

  // ── Infrastructure finishes → handoff → SA ──────────────────────────
  idle("Infrastructure", "NACL rules applied", 8000),
  handoff("Infrastructure", "Solutions Architect"),
  active("Solutions Architect", "Updating architecture decision records", 500),

  // ── SA finishes → handoff → Infrastructure ──────────────────────────
  idle("Solutions Architect", "ADR-003 documented", 8000),
  handoff("Solutions Architect", "Infrastructure"),
  active("Infrastructure", "Configuring DynamoDB tables and access patterns", 500),

  // ── Infrastructure finishes → handoff → Security (final review) ─────
  idle("Infrastructure", "DynamoDB table configuration complete", 8000),
  // Move CI/CD task to review
  taskUpdate("demo-t7", { status: "review" }, 0),
  handoff("Infrastructure", "Security Engineer"),
  active("Security Engineer", "Auditing DynamoDB encryption and backup policies", 500),

  // ── Security finishes — cycle ends ──────────────────────────────────
  idle("Security Engineer", "Audit complete — all checks passed", 8000),
  // Move security review task to done
  taskUpdate("demo-t6", { status: "done" }, 0),
];

// ---------------------------------------------------------------------------
// INTERRUPT — all agents go idle, interrupt fires
// ---------------------------------------------------------------------------

const INTERRUPT_QUESTION =
  "The architecture uses a single DynamoDB table. Should we add a dedicated search index (OpenSearch) for full-text search, or is DynamoDB + GSIs sufficient for the MVP?";

export const INTERRUPT_SEGMENT: TimelineStep[] = [
  // PM announces the pause (shows in activity timeline + center text)
  active("Project Manager", "Pausing work — awaiting customer input", 0),
  // All agents go idle (visual state only — no timeline entries)
  idle("Project Manager", "", 500),
  idle("Solutions Architect", "", 100),
  idle("Infrastructure", "", 100),
  idle("Data Engineer", "", 100),
  idle("Security Engineer", "", 100),
  {
    delayMs: 500,
    event: {
      event: "interrupt_raised",
      project_id: "demo",
      phase: "ARCHITECTURE",
      interrupt_id: "demo-int-1",
      question: INTERRUPT_QUESTION,
    },
  },
  // Inject the question as a PM chat message so it appears in the chat
  {
    delayMs: 100,
    event: {
      event: "chat_message",
      project_id: "demo",
      phase: "ARCHITECTURE",
      message_id: "interrupt-demo-int-1",
      role: "pm",
      content: INTERRUPT_QUESTION,
    },
  },
];

// ---------------------------------------------------------------------------
// APPROVAL — all agents go idle, approval gate fires
// ---------------------------------------------------------------------------

const APPROVAL_QUESTION =
  "The **Architecture** phase is complete. All deliverables have been drafted and reviewed by the team. Please review the artifacts and let us know if you'd like to approve and move to the next phase, or if you have feedback.";

export const APPROVAL_SEGMENT: TimelineStep[] = [
  // PM announces completion (shows in activity timeline + center text)
  active("Project Manager", "Architecture phase complete — preparing for review", 0),
  // All agents go idle (visual state only — no timeline entries)
  idle("Project Manager", "", 500),
  idle("Solutions Architect", "", 100),
  idle("Infrastructure", "", 100),
  idle("Data Engineer", "", 100),
  idle("Security Engineer", "", 100),
  // Move remaining in_progress tasks to done
  taskUpdate("demo-t3", { status: "done" }, 0),
  taskUpdate("demo-t4", { status: "done" }, 0),
  taskUpdate("demo-t5", { status: "done" }, 0),
  taskUpdate("demo-t7", { status: "done" }, 0),
  {
    delayMs: 500,
    event: {
      event: "awaiting_approval",
      project_id: "demo",
      phase: "ARCHITECTURE",
      detail: "Architecture phase ready for review",
    },
  },
  // Inject the approval request as a PM chat message
  {
    delayMs: 100,
    event: {
      event: "chat_message",
      project_id: "demo",
      phase: "ARCHITECTURE",
      message_id: "approval-ARCHITECTURE",
      role: "pm",
      content: APPROVAL_QUESTION,
    },
  },
];

// ---------------------------------------------------------------------------
// RESUME_AFTER_INTERRUPT — agents wake back up
// ---------------------------------------------------------------------------

export const RESUME_SEGMENT: TimelineStep[] = [
  active("Project Manager", "Resuming — customer input received", 0),
  active("Solutions Architect", "Resuming architecture design work", 300),
  active("Data Engineer", "Resuming DynamoDB schema design", 300),
];

// ---------------------------------------------------------------------------
// NEXT_PHASE_SEED — phase advances to POC, new agents activate
// ---------------------------------------------------------------------------

export const NEXT_PHASE_SEED: TimelineStep[] = [
  {
    delayMs: 0,
    event: {
      event: "phase_started",
      project_id: "demo",
      phase: "POC",
      detail: "Proof of Concept phase started",
    },
  },
  {
    delayMs: 500,
    event: {
      event: "agent_active",
      project_id: "demo",
      phase: "POC",
      agent_name: "Developer",
      detail: "Implementing auth proof-of-concept with Cognito",
    },
  },
  {
    delayMs: 300,
    event: {
      event: "agent_active",
      project_id: "demo",
      phase: "POC",
      agent_name: "Infrastructure",
      detail: "Provisioning PoC environment on AWS",
    },
  },
  {
    delayMs: 300,
    event: {
      event: "agent_active",
      project_id: "demo",
      phase: "POC",
      agent_name: "Solutions Architect",
      detail: "Guiding PoC architecture decisions",
    },
  },
  taskUpdate("demo-t10", { status: "in_progress" }, 0),
  taskUpdate("demo-t11", { status: "in_progress" }, 0),
];
