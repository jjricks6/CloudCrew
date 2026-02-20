/**
 * Demo mode simulation for the swarm visualization.
 *
 * Fires a scripted loop of agent_active, agent_idle, and handoff events
 * into the agentStore so the swarm page has visible activity.
 *
 * Only runs when isDemoMode(projectId) is true.
 */

import { useEffect, useRef } from "react";
import { isDemoMode } from "@/lib/demo";
import { useAgentStore } from "@/state/stores/agentStore";

/** A single step in the demo script. */
interface ScriptStep {
  delay: number; // ms after previous step
  event: "agent_active" | "agent_idle" | "handoff";
  agent_name: string;
  detail: string;
}

/**
 * Repeating demo script for the ARCHITECTURE phase.
 *
 * Event ordering for each transition:
 *   1. agent_idle (source finishes)
 *   2. handoff    (arc fires 200ms later)
 *   3. agent_active (destination starts 500ms later)
 *
 * This ensures the activity timeline reads logically:
 *   "IF finished" → "IF handoff → SC" → "SC started: ..."
 *
 * Infrastructure does multiple tasks in a row before handing off.
 * Security always hands back via handoff when finished.
 * Total cycle: ~82 seconds + 2s pause between cycles.
 */
const DEMO_SCRIPT: ScriptStep[] = [
  // ── SA kicks off architecture design ──────────────────────────────
  { delay: 0, event: "agent_active", agent_name: "Solutions Architect",
    detail: "Designing API Gateway integration patterns" },

  // ── SA finishes → handoff → Infrastructure ────────────────────────
  { delay: 8000, event: "agent_idle", agent_name: "Solutions Architect",
    detail: "API Gateway design complete" },
  { delay: 200, event: "handoff", agent_name: "Infrastructure",
    detail: "Handoff from Solutions Architect to Infrastructure" },
  { delay: 500, event: "agent_active", agent_name: "Infrastructure",
    detail: "Provisioning VPC subnets and security groups" },

  // ── Infrastructure does a SECOND task (no handoff — same agent) ───
  { delay: 8000, event: "agent_active", agent_name: "Infrastructure",
    detail: "Configuring NAT gateways and route tables" },

  // ── Infrastructure finishes → handoff → Security ──────────────────
  { delay: 8000, event: "agent_idle", agent_name: "Infrastructure",
    detail: "VPC and routing provisioned" },
  { delay: 200, event: "handoff", agent_name: "Security Engineer",
    detail: "Handoff from Infrastructure to Security Engineer" },
  { delay: 500, event: "agent_active", agent_name: "Security Engineer",
    detail: "Reviewing network ACL and IAM policies" },

  // ── Security finishes → handoff → Infrastructure ──────────────────
  { delay: 10000, event: "agent_idle", agent_name: "Security Engineer",
    detail: "Security review passed — no critical findings" },
  { delay: 200, event: "handoff", agent_name: "Infrastructure",
    detail: "Handoff from Security Engineer to Infrastructure" },
  { delay: 500, event: "agent_active", agent_name: "Infrastructure",
    detail: "Applying security-recommended NACL rules" },

  // ── Infrastructure finishes → handoff → SA ────────────────────────
  { delay: 8000, event: "agent_idle", agent_name: "Infrastructure",
    detail: "NACL rules applied" },
  { delay: 200, event: "handoff", agent_name: "Solutions Architect",
    detail: "Handoff from Infrastructure to Solutions Architect" },
  { delay: 500, event: "agent_active", agent_name: "Solutions Architect",
    detail: "Updating architecture decision records" },

  // ── SA finishes → handoff → Infrastructure ────────────────────────
  { delay: 8000, event: "agent_idle", agent_name: "Solutions Architect",
    detail: "ADR-003 documented" },
  { delay: 200, event: "handoff", agent_name: "Infrastructure",
    detail: "Handoff from Solutions Architect to Infrastructure" },
  { delay: 500, event: "agent_active", agent_name: "Infrastructure",
    detail: "Configuring DynamoDB tables and access patterns" },

  // ── Infrastructure finishes → handoff → Security (final review) ───
  { delay: 8000, event: "agent_idle", agent_name: "Infrastructure",
    detail: "DynamoDB table configuration complete" },
  { delay: 200, event: "handoff", agent_name: "Security Engineer",
    detail: "Handoff from Infrastructure to Security Engineer" },
  { delay: 500, event: "agent_active", agent_name: "Security Engineer",
    detail: "Auditing DynamoDB encryption and backup policies" },

  // ── Security finishes — cycle ends ────────────────────────────────
  { delay: 8000, event: "agent_idle", agent_name: "Security Engineer",
    detail: "Audit complete — all checks passed" },
];

export function useSwarmDemo(projectId: string | undefined) {
  const timeoutsRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    if (!isDemoMode(projectId)) return;

    const addEvent = useAgentStore.getState().addEvent;

    function runCycle() {
      let cumulativeDelay = 0;

      for (const step of DEMO_SCRIPT) {
        cumulativeDelay += step.delay;
        const t = setTimeout(() => {
          addEvent({
            event: step.event,
            project_id: "demo",
            phase: "ARCHITECTURE",
            agent_name: step.agent_name,
            detail: step.detail,
          });
        }, cumulativeDelay);
        timeoutsRef.current.push(t);
      }

      // Schedule next cycle after this one finishes + 2s pause
      const nextCycle = setTimeout(
        () => {
          timeoutsRef.current = [];
          runCycle();
        },
        cumulativeDelay + 2000,
      );
      timeoutsRef.current.push(nextCycle);
    }

    // Start first cycle after a short initial delay
    const initial = setTimeout(runCycle, 1500);
    timeoutsRef.current.push(initial);

    return () => {
      for (const t of timeoutsRef.current) clearTimeout(t);
      timeoutsRef.current = [];
    };
  }, [projectId]);
}
