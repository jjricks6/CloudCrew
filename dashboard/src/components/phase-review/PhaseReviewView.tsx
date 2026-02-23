/**
 * Phase review view — PM polyhedron hero on the left, step-by-step review on the right.
 *
 * User starts by clicking "Review" button in the dashboard. PM then guides through
 * review steps one at a time, showing different artifacts and allowing comments.
 * After all steps, final review shows all content before approval.
 *
 * Layout:
 *   ┌─────────────────────────────────────────────┐
 *   │                                             │
 *   │   ┌──────────┐    ┌──────────────────────┐  │
 *   │   │          │    │  Step title          │  │
 *   │   │   PM     │    │  Step content        │  │
 *   │   │ Polyhedron│    │  (streamed in)       │  │
 *   │   │  (hero)  │    │                      │  │
 *   │   │          │    │  [Comment area]      │  │
 *   │   └──────────┘    │  [Continue]          │  │
 *   │                   └──────────────────────┘  │
 *   │                                             │
 *   └─────────────────────────────────────────────┘
 *
 * Responsive: stacks vertically on narrow screens.
 */

import { AnimatePresence, motion } from "framer-motion";
import { AgentPolyhedron } from "@/components/swarm/AgentPolyhedron";
import { AGENT_CONFIG } from "@/components/swarm/swarm-constants";
import { PhaseReviewStepCard } from "./PhaseReviewStepCard";
import { PhaseReviewFinalCard } from "./PhaseReviewFinalCard";
import { PhaseTransitionCard } from "./PhaseTransitionCard";
import { usePhaseReviewStore } from "@/state/stores/phaseReviewStore";
import {
  useApprovePhase,
  useRevisePhase,
} from "@/state/queries/useApprovalQueries";
import { useProjectId } from "@/lib/useProjectId";
import { useChatStore } from "@/state/stores/chatStore";
import { useAgentStore } from "@/state/stores/agentStore";

const PM_CONFIG = AGENT_CONFIG["Project Manager"];

export function PhaseReviewView() {
  const projectId = useProjectId();
  const status = usePhaseReviewStore((s) => s.status);
  const currentPhase = usePhaseReviewStore((s) => s.currentPhase);
  const pmState = usePhaseReviewStore((s) => s.pmState);
  const steps = usePhaseReviewStore((s) => s.steps);
  const currentStepIndex = usePhaseReviewStore((s) => s.currentStepIndex);
  const currentStepContent = usePhaseReviewStore((s) => s.currentStepContent);

  const approvePhase = useApprovePhase(projectId);
  const revisePhase = useRevisePhase(projectId);

  const isStreaming = pmState === "active";
  const isLoading = approvePhase.isPending || revisePhase.isPending;

  const currentStep = steps[currentStepIndex];

  const handleAddComment = (comment: string) => {
    usePhaseReviewStore.getState().addUserComment(comment);
  };

  const handleContinueStep = () => {
    usePhaseReviewStore.getState().advanceToNextStep();
  };

  const handleApprove = () => {
    useChatStore.getState().addMessage({
      message_id: crypto.randomUUID(),
      role: "customer",
      content: "Approved — looks good, continue to the next phase.",
      timestamp: new Date().toISOString(),
    });

    // Show transition state first, then complete after delay
    usePhaseReviewStore.getState().startTransition();

    setTimeout(() => {
      approvePhase.mutate(undefined, {
        onSuccess: () => {
          useAgentStore.getState().dismissApproval();
          usePhaseReviewStore.getState().completeReview();
        },
      });
    }, 2500);
  };

  const handleRevise = (feedback: string) => {
    useChatStore.getState().addMessage({
      message_id: crypto.randomUUID(),
      role: "customer",
      content: feedback,
      timestamp: new Date().toISOString(),
    });

    revisePhase.mutate(feedback, {
      onSuccess: () => {
        useAgentStore.getState().dismissApproval();
        usePhaseReviewStore.getState().completeReview();
      },
    });
  };

  return (
    <div className="flex h-[calc(100vh-10rem)] items-center justify-center">
      <div className="flex w-full max-w-4xl flex-col items-center gap-8 px-4 md:flex-row md:items-start md:gap-12">
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

        {/* Review content cards */}
        <div className="min-w-0 flex-1">
          <AnimatePresence mode="wait">
            {status === "transitioning" ? (
              <motion.div key="transition">
                <PhaseTransitionCard
                  phaseName={currentPhase || "Current"}
                  message="Thank you for reviewing this phase. Your approval is noted, and we're now preparing the next phase of work. Great collaboration!"
                />
              </motion.div>
            ) : status === "final_review" ? (
              <motion.div key="final">
                <PhaseReviewFinalCard
                  steps={steps}
                  phaseName={currentPhase || "Current"}
                  onApprove={handleApprove}
                  onRequestChanges={handleRevise}
                  isLoading={isLoading}
                />
              </motion.div>
            ) : status === "reviewing" && currentStep ? (
              <motion.div key={`step-${currentStepIndex}`}>
                <PhaseReviewStepCard
                  step={currentStep}
                  currentContent={currentStepContent}
                  isStreaming={isStreaming}
                  onAddComment={handleAddComment}
                  onContinue={handleContinueStep}
                  isLoading={isLoading}
                />
              </motion.div>
            ) : null}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
