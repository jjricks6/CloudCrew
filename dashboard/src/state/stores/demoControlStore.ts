/**
 * Zustand store for demo phase-jump controls.
 *
 * The demo banner UI sets `jumpTarget` via `requestJump()`.
 * The demo engine subscribes and executes the jump, then calls `clearJump()`.
 * `currentPhase` tracks where the demo is for Rewind/Fast Forward index math.
 */

import { create } from "zustand";

export type DemoPhase =
  | "onboarding"
  | "architecture"
  | "poc"
  | "production"
  | "handoff"
  | "complete";

/** Ordered list of jumpable demo phases. */
export const DEMO_PHASES: DemoPhase[] = [
  "onboarding",
  "architecture",
  "poc",
  "production",
  "handoff",
  "complete",
];

/** Human-readable labels for each phase. */
export const DEMO_PHASE_LABELS: Record<DemoPhase, string> = {
  onboarding: "Onboarding",
  architecture: "Architecture",
  poc: "PoC",
  production: "Production",
  handoff: "Handoff",
  complete: "Complete",
};

interface DemoControlState {
  currentPhase: DemoPhase;
  jumpTarget: DemoPhase | null;

  setCurrentPhase: (phase: DemoPhase) => void;
  requestJump: (target: DemoPhase) => void;
  clearJump: () => void;
}

export const useDemoControlStore = create<DemoControlState>((set) => ({
  currentPhase: "onboarding",
  jumpTarget: null,

  setCurrentPhase: (phase) => set({ currentPhase: phase }),
  requestJump: (target) => set({ jumpTarget: target }),
  clearJump: () => set({ jumpTarget: null }),
}));
