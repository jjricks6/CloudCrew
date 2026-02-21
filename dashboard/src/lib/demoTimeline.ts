/**
 * Pure data: scripted event sequences for the demo engine.
 *
 * Each segment is an array of { delayMs, event } steps. The engine plays
 * them sequentially with cumulative delays. Editing the demo means editing
 * this file — the engine (`useDemoEngine.ts`) is a generic scheduler.
 *
 * All events match the WebSocketEvent union so they flow through
 * `agentStore.addEvent()` identically to real backend events.
 *
 * The demo is structured as sequential segments that mirror real backend
 * behavior — no timers. The engine plays each segment in order, pausing
 * only when waiting for user input (interrupt response or approval).
 *
 * Handoff events set the target agent to "thinking" (lit up, pulsing, no
 * spin). The agent transitions to "active" (spinning) when it reports
 * activity via an agent_active event — typically ~2s after the handoff,
 * simulating the agent figuring out what to work on.
 *
 * Flow:
 *   SEED → WORK_BEFORE_INTERRUPT → [wait for user] → RESUME_AND_WORK
 *   → [wait for user] → NEXT_PHASE_SEED → done
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
// WORK_BEFORE_INTERRUPT — agents collaborate, then SA needs customer input
//
// Handoffs set the target to "thinking" (pulsing). An active() event ~2s
// later transitions them to "active" (spinning) with detail text.
// Ends with: SA → PM handoff → PM raises interrupt → PM stays active
// ---------------------------------------------------------------------------

const INTERRUPT_QUESTION =
  "The architecture uses a single DynamoDB table. Should we add a dedicated search index (OpenSearch) for full-text search, or is DynamoDB + GSIs sufficient for the MVP?";

export const WORK_BEFORE_INTERRUPT: TimelineStep[] = [
  // ── SA kicks off architecture design ────────────────────────────────
  active("Solutions Architect", "Designing API Gateway integration patterns", 0),

  // ── SA → Infrastructure ─────────────────────────────────────────────
  handoff("Solutions Architect", "Infrastructure", 8000),
  active("Infrastructure", "Provisioning VPC and subnet resources", 2000),
  taskUpdate("demo-t7", { status: "in_progress" }, 500),
  active("Infrastructure", "Configuring NAT gateways and route tables", 5500),

  // ── Infrastructure → Security ───────────────────────────────────────
  handoff("Infrastructure", "Security Engineer", 8000),
  active("Security Engineer", "Reviewing IAM policies and security groups", 2000),
  taskUpdate("demo-t6", { status: "in_progress" }, 500),

  // ── Security → SA (architecture decision needed) ────────────────────
  handoff("Security Engineer", "Solutions Architect", 8000),
  active("Solutions Architect", "Evaluating search requirements for data model", 2000),
  taskUpdate("demo-t6", { status: "review" }, 0),

  // ── SA needs customer input → SA → PM ───────────────────────────────
  handoff("Solutions Architect", "Project Manager", 5000),
  active("Project Manager", "Preparing question for customer", 2000),
  // PM raises the interrupt — stays active while waiting
  {
    delayMs: 1500,
    event: {
      event: "interrupt_raised",
      project_id: "demo",
      phase: "ARCHITECTURE",
      interrupt_id: "demo-int-1",
      question: INTERRUPT_QUESTION,
    },
  },
  active("Project Manager", "Waiting for customer response", 200),
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
// RESUME_AND_WORK — PM relays answer, work continues, then PM requests
// approval at the end
//
// Ends with: Security → PM handoff → PM raises approval → PM stays active
// ---------------------------------------------------------------------------

const APPROVAL_QUESTION =
  "The **Architecture** phase is complete. All deliverables have been drafted and reviewed by the team. Please review the artifacts and let us know if you'd like to approve and move to the next phase, or if you have feedback.";

export const RESUME_AND_WORK: TimelineStep[] = [
  // ── PM relays customer answer → PM → SA ─────────────────────────────
  active("Project Manager", "Relaying customer response to the team", 0),
  handoff("Project Manager", "Solutions Architect", 1000),
  active("Solutions Architect", "Incorporating customer feedback into architecture", 2000),

  // ── SA resumes → SA → Infrastructure ────────────────────────────────
  handoff("Solutions Architect", "Infrastructure", 6000),
  active("Infrastructure", "Updating VPC configuration per architecture changes", 2000),

  // ── Infrastructure → SA (final docs) ────────────────────────────────
  handoff("Infrastructure", "Solutions Architect", 6000),
  active("Solutions Architect", "Reviewing infrastructure deliverables", 2000),
  taskUpdate("demo-t7", { status: "review" }, 0),

  // ── SA → Infrastructure (DynamoDB) ──────────────────────────────────
  handoff("Solutions Architect", "Infrastructure", 6000),
  active("Infrastructure", "Configuring DynamoDB tables and GSIs", 2000),

  // ── Infrastructure → Security (final review) ────────────────────────
  handoff("Infrastructure", "Security Engineer", 6000),
  active("Security Engineer", "Final security audit of all resources", 2000),

  // ── Security → PM (final review) ───────────────────────────────────
  handoff("Security Engineer", "Project Manager", 6000),
  active("Project Manager", "Reviewing all phase deliverables", 2000),
  taskUpdate("demo-t6", { status: "done" }, 0),

  // ── PM reviews deliverables → moves tasks to done → requests approval
  taskUpdate("demo-t3", { status: "done" }, 2000),
  taskUpdate("demo-t4", { status: "done" }, 500),
  taskUpdate("demo-t5", { status: "done" }, 500),
  taskUpdate("demo-t7", { status: "done" }, 500),
  active("Project Manager", "All deliverables validated — requesting customer approval", 2000),
  {
    delayMs: 1500,
    event: {
      event: "awaiting_approval",
      project_id: "demo",
      phase: "ARCHITECTURE",
      detail: "Architecture phase ready for review",
    },
  },
  active("Project Manager", "Waiting for customer to review deliverables", 200),
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
