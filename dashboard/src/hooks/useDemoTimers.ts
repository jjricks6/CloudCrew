/**
 * Demo mode simulation timers for approval gates and interrupts.
 *
 * Fires one-shot events after delays so the user can experience
 * the approval banner and interrupt bar without a live backend.
 *
 * Only runs when isDemoMode(projectId) is true.
 */

import { useEffect } from "react";
import { isDemoMode, setDemoAwaitingApproval, setDemoAwaitingInput, DEMO_INTERRUPT } from "@/lib/demo";
import { useAgentStore } from "@/state/stores/agentStore";

export function useDemoTimers(projectId: string | undefined) {
  useEffect(() => {
    if (!isDemoMode(projectId)) return;

    const timeouts: ReturnType<typeof setTimeout>[] = [];

    // Fire interrupt after ~30 seconds
    timeouts.push(
      setTimeout(() => {
        setDemoAwaitingInput();
        useAgentStore.getState().addEvent({
          event: "interrupt_raised",
          project_id: "demo",
          phase: DEMO_INTERRUPT.phase,
          interrupt_id: DEMO_INTERRUPT.interrupt_id,
          question: DEMO_INTERRUPT.question,
        });
      }, 30_000),
    );

    // Fire approval gate after ~45 seconds
    timeouts.push(
      setTimeout(() => {
        setDemoAwaitingApproval();
        useAgentStore.getState().addEvent({
          event: "awaiting_approval",
          project_id: "demo",
          phase: "ARCHITECTURE",
          detail: "Architecture phase ready for review",
        });
      }, 45_000),
    );

    return () => {
      for (const t of timeouts) clearTimeout(t);
    };
  }, [projectId]);
}
