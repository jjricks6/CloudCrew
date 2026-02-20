/**
 * Horizontal 5-phase timeline with status-aware indicators.
 *
 * - Completed phases: green check
 * - Active phase: blue pulse
 * - Awaiting approval: yellow pause
 * - Future phases: gray circle
 */

import { PHASE_ORDER, type Phase, type PhaseStatus } from "@/lib/types";
import { PHASE_LABELS } from "@/components/swarm/swarm-constants";

interface PhaseTimelineProps {
  currentPhase?: Phase;
  phaseStatus?: PhaseStatus;
}

function PhaseIcon({
  state,
}: {
  state: "completed" | "active" | "awaiting" | "future";
}) {
  if (state === "completed") {
    return (
      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-green-500 text-white">
        <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path
            fillRule="evenodd"
            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
            clipRule="evenodd"
          />
        </svg>
      </div>
    );
  }

  if (state === "active") {
    return (
      <div className="relative flex h-8 w-8 items-center justify-center">
        <div className="absolute h-8 w-8 animate-ping rounded-full bg-blue-400 opacity-30" />
        <div className="h-4 w-4 rounded-full bg-blue-500" />
      </div>
    );
  }

  if (state === "awaiting") {
    return (
      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-yellow-500 text-white">
        <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path
            fillRule="evenodd"
            d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z"
            clipRule="evenodd"
          />
        </svg>
      </div>
    );
  }

  // future
  return <div className="h-4 w-4 rounded-full bg-muted" />;
}

function getPhaseState(
  phaseIndex: number,
  currentIndex: number,
  phaseStatus?: PhaseStatus,
): "completed" | "active" | "awaiting" | "future" {
  if (phaseIndex < currentIndex) return "completed";
  if (phaseIndex === currentIndex) {
    if (phaseStatus === "AWAITING_APPROVAL") return "awaiting";
    if (phaseStatus === "APPROVED") return "completed";
    return "active";
  }
  return "future";
}

export function PhaseTimeline({
  currentPhase,
  phaseStatus,
}: PhaseTimelineProps) {
  const currentIndex = currentPhase
    ? PHASE_ORDER.indexOf(currentPhase)
    : -1;

  return (
    <div className="flex items-center">
      {PHASE_ORDER.map((phase, i) => {
        const state = getPhaseState(i, currentIndex, phaseStatus);
        const isLast = i === PHASE_ORDER.length - 1;

        return (
          <div key={phase} className="flex items-center" style={isLast ? undefined : { flex: 1 }}>
            <div className="flex flex-col items-center gap-1.5">
              <PhaseIcon state={state} />
              <span
                className={`text-xs font-medium whitespace-nowrap ${
                  state === "future"
                    ? "text-muted-foreground"
                    : "text-foreground"
                }`}
              >
                {PHASE_LABELS[phase]}
              </span>
            </div>
            {!isLast && (
              <div className="mx-2 h-0.5 flex-1">
                <div
                  className={`h-full ${
                    i < currentIndex ? "bg-green-500" : "bg-muted"
                  }`}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
