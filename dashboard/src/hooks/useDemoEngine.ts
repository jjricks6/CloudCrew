/**
 * Consolidated demo engine — runs in AppLayout, drives ALL demo events.
 *
 * The engine is a generic segment player: it reads pure data arrays from
 * `demoTimeline.ts` and schedules them through `agentStore.addEvent()`.
 * Editing the demo sequence means editing `demoTimeline.ts` — this file
 * only handles scheduling, pausing, and reacting to user actions.
 *
 * Flow:
 *   mount → SEED → WORK_LOOP (repeating)
 *   at ~30s → pause work → INTERRUPT
 *   user answers interrupt → RESUME → WORK_LOOP
 *   at ~15s after resume → pause work → APPROVAL
 *   user approves → NEXT_PHASE_SEED → stop (demo complete)
 */

import { useEffect, useRef } from "react";
import { isDemoMode } from "@/lib/demo";
import { useAgentStore } from "@/state/stores/agentStore";
import type { TimelineStep } from "@/lib/demoTimeline";
import {
  SEED_SEGMENT,
  WORK_LOOP_SEGMENT,
  INTERRUPT_SEGMENT,
  APPROVAL_SEGMENT,
  RESUME_SEGMENT,
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
  const workStartRef = useRef(0);

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

    /** Play the work loop, repeating until cancelled. */
    function startWorkLoop() {
      enginePhaseRef.current = "working";
      workStartRef.current = Date.now();

      function runCycle() {
        const duration = playSegment(WORK_LOOP_SEGMENT, () => {
          // Small pause between cycles
          schedule(runCycle, 2000);
        });
        // This is just for the recursive call — duration isn't used here
        void duration;
      }

      runCycle();
    }

    /** Fire interrupt: pause work, idle all agents, fire interrupt event. */
    function fireInterrupt() {
      cancelAll();
      enginePhaseRef.current = "interrupt_pending";
      playSegment(INTERRUPT_SEGMENT);
    }

    /** Resume after interrupt: re-activate agents, restart work loop. */
    function resumeAfterInterrupt() {
      cancelAll();
      enginePhaseRef.current = "resuming";
      const duration = playSegment(RESUME_SEGMENT, () => {
        startWorkLoop();
        // Schedule approval 15s after resume
        schedule(fireApproval, 15_000);
      });
      void duration;
    }

    /** Fire approval: pause work, idle all agents, fire approval event. */
    function fireApproval() {
      cancelAll();
      enginePhaseRef.current = "approval_pending";
      playSegment(APPROVAL_SEGMENT);
    }

    /** Advance to next phase after approval. */
    function advancePhase() {
      cancelAll();
      enginePhaseRef.current = "next_phase";
      playSegment(NEXT_PHASE_SEED, () => {
        enginePhaseRef.current = "done";
      });
    }

    // --- Boot sequence ---
    // 1. Seed agents
    const seedDuration = playSegment(SEED_SEGMENT, () => {
      // 2. Start work loop
      startWorkLoop();
      // 3. Schedule interrupt at 30s from now
      schedule(fireInterrupt, 30_000);
    });
    void seedDuration;

    // --- React to user actions via store subscriptions ---
    const unsubscribe = useAgentStore.subscribe((state, prevState) => {
      // User answered interrupt → resume work
      if (
        prevState.pendingInterrupt !== null &&
        state.pendingInterrupt === null &&
        enginePhaseRef.current === "interrupt_pending"
      ) {
        resumeAfterInterrupt();
      }

      // User dismissed approval → advance phase
      if (
        prevState.pendingApproval !== null &&
        state.pendingApproval === null &&
        enginePhaseRef.current === "approval_pending"
      ) {
        advancePhase();
      }
    });

    return () => {
      cancelAll();
      unsubscribe();
    };
  }, [projectId]);
}
