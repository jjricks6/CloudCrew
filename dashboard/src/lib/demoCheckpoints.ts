/**
 * Demo checkpoints — reset all state to a known point for phase-jump controls.
 *
 * Each checkpoint atomically resets Zustand stores and mutable demo data,
 * then sets the phase-specific state (agents, interrupts, project status, etc.).
 */

import { useAgentStore } from "@/state/stores/agentStore";
import { useChatStore } from "@/state/stores/chatStore";
import { useOnboardingStore } from "@/state/stores/onboardingStore";
import {
  resetDemoData,
  DEMO_PROJECT_STATUS,
  DEMO_BOARD_TASKS,
  DEMO_CHAT_HISTORY,
} from "@/lib/demo";
import { queryClient } from "@/state/queryClient";
import type { DemoPhase } from "@/state/stores/demoControlStore";
import type { AgentActivity } from "@/lib/types";
import { PHASE_PLAYBOOKS } from "@/lib/demoTimeline";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function mk(name: string, status: AgentActivity["status"], phase: string, detail: string): AgentActivity {
  return { agent_name: name, status, phase, detail, timestamp: Date.now() };
}

/** Mark all tasks for a phase as done. */
function completePhaseTasks(phase: string): void {
  for (const task of DEMO_BOARD_TASKS) {
    if (task.phase === phase) {
      task.status = "done";
      task.updated_at = new Date().toISOString();
    }
  }
}

/** Deliverable definitions per phase, used by both timeline and checkpoints. */
const PHASE_DELIVERABLES: Record<string, { name: string; git_path: string }[]> = {
  ARCHITECTURE: [
    { name: "Data Model", git_path: "docs/data-model.md" },
    { name: "System Architecture", git_path: "docs/architecture.md" },
    { name: "API Contracts", git_path: "docs/api-contracts.md" },
    { name: "Test Strategy", git_path: "docs/test-strategy.md" },
  ],
  POC: [
    { name: "Auth Proof-of-Concept", git_path: "poc/auth-poc.md" },
    { name: "Load Test Results", git_path: "poc/load-test-results.md" },
    { name: "Migration Runbook Draft", git_path: "poc/migration-runbook.md" },
  ],
  PRODUCTION: [
    { name: "Deployment Guide", git_path: "production/deployment-guide.md" },
    { name: "Monitoring Configuration", git_path: "production/monitoring.md" },
    { name: "Data Migration Report", git_path: "production/migration-report.md" },
  ],
  HANDOFF: [
    { name: "Operations Runbook", git_path: "handoff/operations-runbook.md" },
    { name: "API Documentation", git_path: "handoff/api-docs.md" },
    { name: "Compliance Report", git_path: "handoff/compliance-report.md" },
    { name: "Training Materials", git_path: "handoff/training-materials.md" },
  ],
};

/** Seed all deliverables for a phase at v1.0 (used when jumping past a phase). */
function seedDeliverables(phase: string): void {
  const items = PHASE_DELIVERABLES[phase];
  if (!items) return;
  DEMO_PROJECT_STATUS.deliverables[phase] = items.map((d) => ({
    name: d.name,
    git_path: d.git_path,
    version: "v1.0",
    created_at: new Date().toISOString(),
  }));
}

/** Advance project to a given phase with all prior phases completed. */
function advanceTo(targetPhase: string): void {
  const order = ["DISCOVERY", "ARCHITECTURE", "POC", "PRODUCTION", "HANDOFF"];
  const idx = order.indexOf(targetPhase);
  for (let i = 0; i < idx; i++) {
    completePhaseTasks(order[i]);
    seedDeliverables(order[i]);
  }
  DEMO_PROJECT_STATUS.current_phase = targetPhase as typeof DEMO_PROJECT_STATUS.current_phase;
  DEMO_PROJECT_STATUS.phase_status = "IN_PROGRESS";
}

// ---------------------------------------------------------------------------
// Agent snapshots for mid-phase checkpoints
// ---------------------------------------------------------------------------

function archInterruptAgents(): AgentActivity[] {
  return [
    mk("Solutions Architect", "idle", "ARCHITECTURE", "Evaluating search requirements for data model"),
    mk("Data Engineer", "idle", "ARCHITECTURE", "Mapping entity relationships to GSI projections"),
    mk("Security Engineer", "idle", "ARCHITECTURE", "Evaluating Cognito token scoping and network boundaries"),
    mk("Project Manager", "active", "ARCHITECTURE", "Waiting for customer response"),
  ];
}

/** Phase-start snapshot: only PM is active (playbook handles the handoff). */
function phaseStartAgents(phase: string): AgentActivity[] {
  return [mk("Project Manager", "active", phase, `Kicking off the ${phase} phase`)];
}

// ---------------------------------------------------------------------------
// Checkpoint application
// ---------------------------------------------------------------------------

/** Reset all demo state and configure it for the given phase. */
export function applyCheckpoint(phase: DemoPhase): void {
  // 1. Reset everything to factory defaults
  useAgentStore.getState().reset();
  useChatStore.getState().reset();
  useOnboardingStore.getState().reset();
  resetDemoData();

  // 2. Apply phase-specific state
  switch (phase) {
    case "onboarding":
      // Fresh start — onboardingStore already reset to not_started
      break;

    case "architecture":
      useOnboardingStore.getState().complete();
      useChatStore.getState().loadHistory(DEMO_CHAT_HISTORY);
      // Agents appear via playback
      break;

    case "poc":
      useOnboardingStore.getState().complete();
      useChatStore.getState().loadHistory(DEMO_CHAT_HISTORY);
      advanceTo("POC");
      useAgentStore.setState({ agents: phaseStartAgents("POC"), wsStatus: "connected" });
      break;

    case "production":
      useOnboardingStore.getState().complete();
      useChatStore.getState().loadHistory(DEMO_CHAT_HISTORY);
      advanceTo("PRODUCTION");
      useAgentStore.setState({ agents: phaseStartAgents("PRODUCTION"), wsStatus: "connected" });
      break;

    case "handoff":
      useOnboardingStore.getState().complete();
      useChatStore.getState().loadHistory(DEMO_CHAT_HISTORY);
      advanceTo("HANDOFF");
      useAgentStore.setState({ agents: phaseStartAgents("HANDOFF"), wsStatus: "connected" });
      break;

    case "complete":
      useOnboardingStore.getState().complete();
      useChatStore.getState().loadHistory(DEMO_CHAT_HISTORY);
      advanceTo("HANDOFF");
      completePhaseTasks("HANDOFF");
      seedDeliverables("HANDOFF");
      DEMO_PROJECT_STATUS.phase_status = "APPROVED";
      useAgentStore.setState({
        agents: [mk("Project Manager", "active", "HANDOFF", "Engagement complete — presenting final deliverables")],
        wsStatus: "connected",
      });
      break;
  }

  // 3. Invalidate queries so TanStack re-reads mutable demo data
  void queryClient.invalidateQueries({ queryKey: ["project"] });
  void queryClient.invalidateQueries({ queryKey: ["board-tasks"] });
  void queryClient.invalidateQueries({ queryKey: ["deliverables"] });
}

/**
 * Get the interrupt agent snapshot for a specific playbook phase.
 * Used when jumping directly to a phase's interrupt state.
 */
export function getInterruptSnapshot(playbookPhase: string): AgentActivity[] {
  if (playbookPhase === "ARCHITECTURE") return archInterruptAgents();
  // For other phases, build a generic snapshot
  const playbook = PHASE_PLAYBOOKS.find((p) => p.phase === playbookPhase);
  if (!playbook?.interrupt) return [];
  return [mk("Project Manager", "active", playbookPhase, "Waiting for customer response")];
}
