/**
 * Horizontal 5-phase timeline with status-aware indicators.
 *
 * - Completed phases: green check
 * - Active phase: blue pulse
 * - Awaiting approval/input: yellow circle
 * - Future phases: gray circle
 */

import { motion, AnimatePresence } from "framer-motion";
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
      <div className="flex h-5 w-5 items-center justify-center rounded-full bg-green-500 text-white md:h-8 md:w-8">
        <svg className="h-3 w-3 md:h-4 md:w-4" viewBox="0 0 20 20" fill="currentColor">
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
      <div className="relative flex h-5 w-5 items-center justify-center md:h-8 md:w-8">
        <div className="absolute h-5 w-5 animate-ping rounded-full bg-blue-400 opacity-30 md:h-8 md:w-8" />
        <div className="h-2.5 w-2.5 rounded-full bg-blue-500 md:h-4 md:w-4" />
      </div>
    );
  }

  if (state === "awaiting") {
    return (
      <div className="flex h-5 w-5 items-center justify-center md:h-8 md:w-8">
        <div className="h-2.5 w-2.5 rounded-full bg-yellow-500 md:h-4 md:w-4" />
      </div>
    );
  }

  // future
  return (
    <div className="flex h-5 w-5 items-center justify-center md:h-8 md:w-8">
      <div className="h-2.5 w-2.5 rounded-full bg-muted md:h-4 md:w-4" />
    </div>
  );
}

function getPhaseState(
  phaseIndex: number,
  currentIndex: number,
  phaseStatus?: PhaseStatus,
): "completed" | "active" | "awaiting" | "future" {
  if (phaseIndex < currentIndex) return "completed";
  if (phaseIndex === currentIndex) {
    if (phaseStatus === "AWAITING_APPROVAL" || phaseStatus === "AWAITING_INPUT")
      return "awaiting";
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
    <div className="flex flex-col gap-1 md:gap-1.5">
      {/* Dots + connecting lines row */}
      <div className="flex items-center">
        {PHASE_ORDER.map((phase, i) => {
          const state = getPhaseState(i, currentIndex, phaseStatus);
          const isLast = i === PHASE_ORDER.length - 1;

          return (
            <div key={phase} className="flex items-center" style={isLast ? undefined : { flex: 1 }}>
              {/* Fixed-size wrapper keeps layout stable during animation */}
              <div className="flex h-5 w-5 shrink-0 items-center justify-center md:h-8 md:w-8">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={state}
                    initial={{ opacity: 0, scale: 0.5 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.5 }}
                    transition={{ duration: 0.35, ease: "easeInOut" }}
                    className="flex items-center justify-center"
                  >
                    <PhaseIcon state={state} />
                  </motion.div>
                </AnimatePresence>
              </div>
              {!isLast && (
                <div className="mx-0.5 h-0.5 flex-1 overflow-hidden rounded-full bg-muted md:mx-1">
                  <div
                    className="h-full origin-left bg-green-500 transition-transform duration-700 ease-in-out"
                    style={{ transform: `scaleX(${i < currentIndex ? 1 : 0})` }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Labels row — evenly spaced to match dots */}
      <div className="flex justify-between">
        {PHASE_ORDER.map((phase) => {
          const state = getPhaseState(
            PHASE_ORDER.indexOf(phase),
            currentIndex,
            phaseStatus,
          );
          return (
            <span
              key={phase}
              className={`text-center text-[10px] font-medium md:text-xs ${
                state === "future"
                  ? "text-muted-foreground"
                  : "text-foreground"
              }`}
            >
              {PHASE_LABELS[phase]}
            </span>
          );
        })}
      </div>
    </div>
  );
}
