/**
 * Consolidated demo engine — runs in AppLayout, drives ALL demo events.
 *
 * The engine is a generic segment player: it reads pure data arrays from
 * `demoTimeline.ts` and schedules them through `agentStore.addEvent()`.
 * Editing the demo sequence means editing `demoTimeline.ts` — this file
 * only handles scheduling and reacting to user actions.
 *
 * No timers control the flow — interrupts and approvals emerge naturally
 * from the agent handoff sequence, just like the real backend. The only
 * pauses are when the engine waits for user input.
 *
 * Flow:
 *   mount → SEED → WORK_BEFORE_INTERRUPT → [wait for user response]
 *   → RESUME_AND_WORK → [wait for user approval]
 *   → NEXT_PHASE_SEED → done
 */

import { useEffect, useRef } from "react";
import { isDemoMode } from "@/lib/demo";
import { useAgentStore } from "@/state/stores/agentStore";
import type { TimelineStep } from "@/lib/demoTimeline";
import {
  SEED_SEGMENT,
  WORK_BEFORE_INTERRUPT,
  RESUME_AND_WORK,
  NEXT_PHASE_SEED,
} from "@/lib/demoTimeline";

type EnginePhase =
  | "seed"
  | "working"
  | "interrupt_pending"
  | "resuming"
  | "approval_pending"
  | "next_phase"
  | "done";

export function useDemoEngine(projectId: string | undefined) {
  const timeoutsRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const enginePhaseRef = useRef<EnginePhase>("seed");

  useEffect(() => {
    if (!isDemoMode(projectId)) return;

    const addEvent = useAgentStore.getState().addEvent;

    function schedule(fn: () => void, ms: number) {
      const t = setTimeout(fn, ms);
      timeoutsRef.current.push(t);
      return t;
    }

    function cancelAll() {
      for (const t of timeoutsRef.current) clearTimeout(t);
      timeoutsRef.current = [];
    }

    /**
     * Play a segment: schedule each step with cumulative delay.
     * Returns the total duration so callers can schedule follow-ups.
     */
    function playSegment(
      steps: TimelineStep[],
      onComplete?: () => void,
    ): number {
      let cumulative = 0;
      for (const step of steps) {
        cumulative += step.delayMs;
        const event = step.event;
        schedule(() => addEvent(event), cumulative);
      }
      if (onComplete) {
        schedule(onComplete, cumulative + 100);
      }
      return cumulative;
    }

    // --- Boot sequence ---
    // 1. Seed agents (if any)
    // 2. Play work → naturally ends with interrupt
    playSegment(SEED_SEGMENT, () => {
      enginePhaseRef.current = "working";
      playSegment(WORK_BEFORE_INTERRUPT, () => {
        enginePhaseRef.current = "interrupt_pending";
        // Now we wait for the user to respond to the interrupt.
        // The store subscription below handles the transition.
      });
    });

    // --- React to user actions via store subscriptions ---
    const unsubscribe = useAgentStore.subscribe((state, prevState) => {
      // User answered interrupt → play resume + more work → ends with approval
      if (
        prevState.pendingInterrupt !== null &&
        state.pendingInterrupt === null &&
        enginePhaseRef.current === "interrupt_pending"
      ) {
        cancelAll();
        enginePhaseRef.current = "resuming";
        playSegment(RESUME_AND_WORK, () => {
          enginePhaseRef.current = "approval_pending";
          // Now we wait for the user to approve/revise.
        });
      }

      // User dismissed approval → advance to next phase
      if (
        prevState.pendingApproval !== null &&
        state.pendingApproval === null &&
        enginePhaseRef.current === "approval_pending"
      ) {
        cancelAll();
        enginePhaseRef.current = "next_phase";
        playSegment(NEXT_PHASE_SEED, () => {
          enginePhaseRef.current = "done";
        });
      }
    });

    return () => {
      cancelAll();
      unsubscribe();
      enginePhaseRef.current = "seed";
    };
  }, [projectId]);
}
