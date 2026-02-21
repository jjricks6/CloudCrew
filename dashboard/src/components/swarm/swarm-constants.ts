/**
 * Constants for the swarm visualization: agent colors, abbreviations,
 * phase-to-agent mappings, and radial positioning math.
 */

import type { Phase } from "@/lib/types";

// ---------------------------------------------------------------------------
// Phase labels (shared across PhaseTimeline, CenterHub, etc.)
// ---------------------------------------------------------------------------

export const PHASE_LABELS: Record<Phase, string> = {
  DISCOVERY: "Discovery",
  ARCHITECTURE: "Architecture",
  POC: "PoC",
  PRODUCTION: "Production",
  HANDOFF: "Handoff",
  RETROSPECTIVE: "Retro",
};

// ---------------------------------------------------------------------------
// Agent identity
// ---------------------------------------------------------------------------

export type AgentShape =
  | "dodecahedron"
  | "icosahedron"
  | "octahedron"
  | "box"
  | "tetrahedron"
  | "gem"
  | "cone";

export interface AgentConfig {
  key: string;
  abbr: string;
  color: string;
  label: string;
  shape: AgentShape;
}

/** Maps full agent name → visual config. */
export const AGENT_CONFIG: Record<string, AgentConfig> = {
  "Project Manager": { key: "pm", abbr: "PM", color: "#3b82f6", label: "Project Manager", shape: "dodecahedron" },
  "Solutions Architect": { key: "sa", abbr: "SA", color: "#a855f7", label: "Solutions Architect", shape: "icosahedron" },
  Developer: { key: "dev", abbr: "DV", color: "#22c55e", label: "Developer", shape: "octahedron" },
  Infrastructure: { key: "infra", abbr: "IF", color: "#f97316", label: "Infrastructure", shape: "box" },
  "Data Engineer": { key: "data", abbr: "DA", color: "#06b6d4", label: "Data Engineer", shape: "tetrahedron" },
  "Security Engineer": { key: "security", abbr: "SC", color: "#f43f5e", label: "Security", shape: "gem" },
  "QA Engineer": { key: "qa", abbr: "QA", color: "#f59e0b", label: "QA Engineer", shape: "cone" },
};

/** All agent names in consistent display order. */
export const ALL_AGENTS = Object.keys(AGENT_CONFIG);

/** Fallback config for unknown agents. */
const UNKNOWN_AGENT: AgentConfig = {
  key: "unknown",
  abbr: "??",
  color: "#6b7280",
  label: "Unknown",
  shape: "octahedron",
};

export function getAgentConfig(name: string): AgentConfig {
  return AGENT_CONFIG[name] ?? UNKNOWN_AGENT;
}

// ---------------------------------------------------------------------------
// Phase → agents mapping (matches backend swarm composition)
// ---------------------------------------------------------------------------

export const PHASE_AGENTS: Partial<Record<Phase, string[]>> = {
  DISCOVERY: ["Project Manager", "Solutions Architect"],
  ARCHITECTURE: ["Project Manager", "Solutions Architect", "Infrastructure", "Security Engineer"],
  POC: ["Project Manager", "Developer", "Infrastructure", "Data Engineer", "Security Engineer", "Solutions Architect"],
  PRODUCTION: ["Project Manager", "Developer", "Infrastructure", "Data Engineer", "Security Engineer", "QA Engineer"],
  HANDOFF: ["Project Manager", "Solutions Architect"],
};

// ---------------------------------------------------------------------------
// Radial positioning
// ---------------------------------------------------------------------------

export interface AgentPosition {
  name: string;
  x: number;
  y: number;
}

/**
 * Compute radial positions for agents around a center point.
 * Agents are placed evenly on a circle starting from the top (12 o'clock).
 */
export function getAgentPositions(
  agents: string[],
  width: number,
  height: number,
): AgentPosition[] {
  const centerX = width / 2;
  const centerY = height / 2;
  // Use 55% of the smaller dimension so thought bubbles have room
  const radius = Math.min(centerX, centerY) * 0.55;
  const count = agents.length;
  const startAngle = -Math.PI / 2; // top of circle

  return agents.map((name, i) => {
    const angle = startAngle + (2 * Math.PI * i) / count;
    return {
      name,
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    };
  });
}

// ---------------------------------------------------------------------------
// Sizing — scales dynamically based on container dimensions
// ---------------------------------------------------------------------------

export const NODE_SIZE_ACTIVE = 110;
export const NODE_SIZE_IDLE = 88;

function clamp(min: number, value: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export interface NodeSizes {
  active: number;
  idle: number;
  fontSize: number;
  labelSize: number;
}

/** Compute node sizes that scale with the container. */
export function getNodeSizes(width: number, height: number): NodeSizes {
  const minDim = Math.min(width, height);
  const active = Math.round(clamp(88, minDim * 0.18, 160));
  const idle = Math.round(active * 0.8);
  const fontSize = Math.round(clamp(14, active * 0.16, 22));
  const labelSize = Math.round(clamp(10, active * 0.1, 14));
  return { active, idle, fontSize, labelSize };
}
