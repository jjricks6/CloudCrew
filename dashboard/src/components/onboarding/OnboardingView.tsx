/**
 * Onboarding view — PM polyhedron hero on the left, question card on the right.
 *
 * This replaces the normal DashboardPage content when onboarding is not yet
 * complete. The PM agent guides the user through project setup one question
 * at a time, culminating in a SOW review and approval.
 *
 * Layout:
 *   ┌─────────────────────────────────────────────┐
 *   │                                             │
 *   │   ┌──────────┐    ┌──────────────────────┐  │
 *   │   │          │    │  PM question text     │  │
 *   │   │   PM     │    │  (streamed in)        │  │
 *   │   │ Polyhedron│    │                      │  │
 *   │   │  (hero)  │    │  [Input area]         │  │
 *   │   │          │    │  [Send] [Upload]      │  │
 *   │   └──────────┘    └──────────────────────┘  │
 *   │                                             │
 *   └─────────────────────────────────────────────┘
 *
 * Responsive: stacks vertically on narrow screens.
 */

import { AnimatePresence, motion } from "framer-motion";
import { AgentPolyhedron } from "@/components/swarm/AgentPolyhedron";
import { AGENT_CONFIG } from "@/components/swarm/swarm-constants";
import { OnboardingQuestionCard } from "./OnboardingQuestionCard";
import { SowReviewCard } from "./SowReviewCard";
import { WrapupCard } from "./WrapupCard";
import { useOnboardingStore } from "@/state/stores/onboardingStore";
import { ONBOARDING_STEPS, REVISION_STEP } from "@/lib/onboardingDemoTimeline";

const PM_CONFIG = AGENT_CONFIG["Project Manager"];

export function OnboardingView() {
  const status = useOnboardingStore((s) => s.status);
  const currentStep = useOnboardingStore((s) => s.currentStep);
  const pmState = useOnboardingStore((s) => s.pmState);
  const questionText = useOnboardingStore((s) => s.currentQuestionText);
  const sowContent = useOnboardingStore((s) => s.sowContent);
  const isRevision = useOnboardingStore((s) => s.isRevision);

  const step = isRevision ? REVISION_STEP : ONBOARDING_STEPS[currentStep];
  const isStreaming = pmState === "active";

  return (
    <div className="flex h-[calc(100vh-10rem)] items-center justify-center">
      <div className="flex w-full max-w-4xl flex-col items-center gap-8 px-4 md:flex-row md:items-center md:gap-12">
        {/* PM Polyhedron — hero sized */}
        <div className="flex shrink-0 flex-col items-center gap-3">
          <div className="relative" style={{ width: 260, height: 260 }}>
            <AgentPolyhedron
              shape={PM_CONFIG.shape}
              color={PM_CONFIG.color}
              status={pmState}
            />
            {/* PM label centered over polyhedron */}
            <span
              className="pointer-events-none absolute inset-0 flex items-center justify-center text-2xl font-bold"
              style={{ color: PM_CONFIG.color, opacity: 0.7 }}
            >
              PM
            </span>
          </div>
          <p className="text-sm font-medium text-muted-foreground">
            Project Manager
          </p>
        </div>

        {/* Question / SOW review card */}
        <div className="min-w-0 flex-1">
          <AnimatePresence mode="wait">
            {status === "wrapup" ? (
              <motion.div key="wrapup">
                <WrapupCard
                  messageText={questionText}
                  isStreaming={isStreaming}
                />
              </motion.div>
            ) : status === "sow_review" ? (
              <motion.div key="sow">
                <SowReviewCard sowContent={sowContent} />
              </motion.div>
            ) : step ? (
              <motion.div key={isRevision ? "revision" : `step-${currentStep}`}>
                <OnboardingQuestionCard
                  step={step}
                  questionText={questionText}
                  isStreaming={isStreaming}
                />
              </motion.div>
            ) : null}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
