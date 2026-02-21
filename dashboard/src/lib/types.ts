/**
 * Shared TypeScript types matching backend Pydantic models.
 *
 * These types mirror src/state/models.py and the WebSocket event schemas.
 * Any changes to backend models must be reflected here manually.
 */

// --- Enums (matching backend StrEnum values) ---

export const Phase = {
  DISCOVERY: "DISCOVERY",
  ARCHITECTURE: "ARCHITECTURE",
  POC: "POC",
  PRODUCTION: "PRODUCTION",
  HANDOFF: "HANDOFF",
  RETROSPECTIVE: "RETROSPECTIVE",
} as const;
export type Phase = (typeof Phase)[keyof typeof Phase];

/** Phases displayed in the timeline (excludes RETROSPECTIVE — deferred to M6). */
export const PHASE_ORDER: Phase[] = [
  Phase.DISCOVERY,
  Phase.ARCHITECTURE,
  Phase.POC,
  Phase.PRODUCTION,
  Phase.HANDOFF,
];

export const PhaseStatus = {
  IN_PROGRESS: "IN_PROGRESS",
  AWAITING_APPROVAL: "AWAITING_APPROVAL",
  AWAITING_INPUT: "AWAITING_INPUT",
  APPROVED: "APPROVED",
  REVISION_REQUESTED: "REVISION_REQUESTED",
} as const;
export type PhaseStatus = (typeof PhaseStatus)[keyof typeof PhaseStatus];

// --- Task Ledger ---

export interface DeliverableItem {
  name: string;
  git_path: string;
  status: "IN_PROGRESS" | "COMPLETE" | "NEEDS_REVISION";
}

export interface Fact {
  description: string;
  source: string;
  timestamp: string;
}

export interface Assumption {
  description: string;
  confidence: "HIGH" | "MEDIUM" | "LOW";
  timestamp: string;
}

export interface Decision {
  description: string;
  rationale: string;
  made_by: string;
  timestamp: string;
  adr_path: string;
}

export interface Blocker {
  description: string;
  assigned_to: string;
  status: "OPEN" | "RESOLVED";
  timestamp: string;
}

export interface ProjectStatus {
  project_id: string;
  project_name: string;
  current_phase: Phase;
  phase_status: PhaseStatus;
  deliverables: Record<string, DeliverableItem[]>;
  facts: Fact[];
  assumptions: Assumption[];
  decisions: Decision[];
  blockers: Blocker[];
  created_at: string;
  updated_at: string;
}

/** Slim response from GET /projects/{id}/status (subset of full ProjectStatus). */
export interface ProjectStatusSummary {
  project_id: string;
  project_name: string;
  current_phase: Phase;
  phase_status: PhaseStatus;
}

// --- WebSocket Events ---

interface BaseEvent {
  project_id: string;
  phase: string;
}

export interface AgentActiveEvent extends BaseEvent {
  event: "agent_active";
  agent_name: string;
  detail: string;
}

export interface AgentIdleEvent extends BaseEvent {
  event: "agent_idle";
  agent_name: string;
  detail: string;
}

export interface HandoffEvent extends BaseEvent {
  event: "handoff";
  agent_name: string;
  detail: string;
}

export interface PhaseStartedEvent extends BaseEvent {
  event: "phase_started";
  detail: string;
}

export interface AwaitingApprovalEvent extends BaseEvent {
  event: "awaiting_approval";
  detail: string;
}

export interface InterruptRaisedEvent extends BaseEvent {
  event: "interrupt_raised";
  interrupt_id: string;
  question: string;
}

export interface ChatMessageEvent extends BaseEvent {
  event: "chat_message";
  message_id: string;
  role: "customer" | "pm";
  content: string;
}

export interface ChatThinkingEvent extends BaseEvent {
  event: "chat_thinking";
}

export interface ChatChunkEvent extends BaseEvent {
  event: "chat_chunk";
  content: string;
}

export interface ChatDoneEvent extends BaseEvent {
  event: "chat_done";
  message_id: string;
}

export type WebSocketEvent =
  | AgentActiveEvent
  | AgentIdleEvent
  | HandoffEvent
  | PhaseStartedEvent
  | AwaitingApprovalEvent
  | InterruptRaisedEvent
  | ChatMessageEvent
  | ChatThinkingEvent
  | ChatChunkEvent
  | ChatDoneEvent
  | TaskCreatedEvent
  | TaskUpdatedEvent;

// --- Board Tasks (Kanban) ---

export const KanbanColumn = {
  BACKLOG: "backlog",
  IN_PROGRESS: "in_progress",
  REVIEW: "review",
  DONE: "done",
} as const;
export type KanbanColumn = (typeof KanbanColumn)[keyof typeof KanbanColumn];

export const KANBAN_COLUMNS: KanbanColumn[] = [
  KanbanColumn.BACKLOG,
  KanbanColumn.IN_PROGRESS,
  KanbanColumn.REVIEW,
  KanbanColumn.DONE,
];

export interface TaskComment {
  author: string;
  content: string;
  timestamp: string;
}

export interface BoardTask {
  task_id: string;
  title: string;
  description: string;
  phase: string;
  status: KanbanColumn;
  assigned_to: string;
  comments: TaskComment[];
  artifact_path: string;
  created_at: string;
  updated_at: string;
}

export interface TaskCreatedEvent extends BaseEvent {
  event: "task_created";
  task_id: string;
  title: string;
  assigned_to: string;
}

export interface TaskUpdatedEvent extends BaseEvent {
  event: "task_updated";
  task_id: string;
  updates: Record<string, unknown>;
}

// --- Chat Message (REST + Zustand store) ---

export interface ChatMessage {
  message_id: string;
  role: "customer" | "pm";
  content: string;
  timestamp: string;
}

// --- Agent Activity (for Zustand store) ---

export interface AgentActivity {
  agent_name: string;
  status: "active" | "idle" | "thinking";
  phase: string;
  detail: string;
  timestamp: number;
}

// --- Swarm Timeline (for swarm visualization) ---

export interface SwarmTimelineEvent {
  id: string;
  type: "agent_active" | "agent_idle" | "handoff";
  agentName: string;
  detail: string;
  phase: string;
  timestamp: number;
  fromAgent?: string; // only for handoff events
}

// --- Connection Status ---

export type WsStatus = "connecting" | "connected" | "disconnected";
