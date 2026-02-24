/**
 * Phase review view — PM polyhedron hero on the left, simplified review flow on the right.
 *
 * User starts by clicking "Review" button. PM shows:
 * 1. Opening message (with Continue button)
 * 2. Artifact review screen (with chat and approval)
 * 3. Closing message (auto-fades)
 *
 * Layout:
 *   ┌─────────────────────────────────────────────┐
 *   │                                             │
 *   │   ┌──────────┐    ┌──────────────────────┐  │
 *   │   │          │    │  Opening/Artifacts/  │  │
 *   │   │   PM     │    │  Closing Message     │  │
 *   │   │ Polyhedron│    │                      │  │
 *   │   │  (hero)  │    │  [Action Buttons]    │  │
 *   │   │          │    │                      │  │
 *   │   └──────────┘    └──────────────────────┘  │
 *   │                                             │
 *   └─────────────────────────────────────────────┘
 *
 * Responsive: stacks vertically on narrow screens.
 */

import { AnimatePresence, motion } from "framer-motion";
import { AgentPolyhedron } from "@/components/swarm/AgentPolyhedron";
import { AGENT_CONFIG } from "@/components/swarm/swarm-constants";
import { Button } from "@/components/ui/button";
import { PhaseReviewMessageCard } from "./PhaseReviewMessageCard";
import { PhaseReviewArtifactView } from "./PhaseReviewArtifactView";
import { usePhaseReviewStore } from "@/state/stores/phaseReviewStore";
import { useApprovePhase } from "@/state/queries/useApprovalQueries";
import { useProjectId } from "@/lib/useProjectId";
import { useProjectDeliverables } from "@/state/queries/useProjectQueries";
import { useChatStore } from "@/state/stores/chatStore";
import { useAgentStore } from "@/state/stores/agentStore";

const PM_CONFIG = AGENT_CONFIG["Project Manager"];

export function PhaseReviewView() {
  const projectId = useProjectId();
  const { data: deliverables } = useProjectDeliverables(projectId);

  const status = usePhaseReviewStore((s) => s.status);
  const currentPhase = usePhaseReviewStore((s) => s.currentPhase);
  const pmState = usePhaseReviewStore((s) => s.pmState);

  // Opening message
  const openingMessage = usePhaseReviewStore((s) => s.openingMessage);
  const openingContent = usePhaseReviewStore((s) => s.openingContent);

  // Artifact review
  const phaseSummaryPath = usePhaseReviewStore((s) => s.phaseSummaryPath);
  const chatHistory = usePhaseReviewStore((s) => s.chatHistory);
  const currentChatContent = usePhaseReviewStore((s) => s.currentChatContent);

  // Closing message
  const closingMessage = usePhaseReviewStore((s) => s.closingMessage);
  const closingContent = usePhaseReviewStore((s) => s.closingContent);

  const approvePhase = useApprovePhase(projectId);

  const isLoading = approvePhase.isPending;
  const isChatStreaming = pmState === "active";

  // Get artifacts from project data, excluding Phase Summary
  const artifacts = currentPhase && deliverables
    ? (deliverables[currentPhase] || []).filter(
        (item) => item.name !== "Phase Summary"
      )
    : [];

  const handleOpeningContinue = () => {
    usePhaseReviewStore.getState().advanceToArtifactReview();
  };

  const handleClosingContinue = () => {
    usePhaseReviewStore.getState().advanceFromClosing();
  };

  const handleSendChatMessage = (message: string) => {
    usePhaseReviewStore.getState().addUserChatMessage(message);
    // Demo engine will handle streaming PM response
  };

  const handleApprove = () => {
    useChatStore.getState().addMessage({
      message_id: crypto.randomUUID(),
      role: "customer",
      content: "Approved — looks good, continue to the next phase.",
      timestamp: new Date().toISOString(),
    });

    // Advance to closing message (use the message from playbook)
    usePhaseReviewStore.getState().advanceToClosingMessage(closingMessage);
  };

  const handleStartNextPhase = () => {
    approvePhase.mutate(undefined, {
      onSuccess: () => {
        useAgentStore.getState().dismissApproval();
        usePhaseReviewStore.getState().completeReview();
      },
    });
  };


  return (
    <div className="flex h-[calc(100vh-10rem)] items-center justify-center overflow-hidden">
      <div className="flex w-full max-w-6xl flex-col items-center gap-8 px-4 md:flex-row md:items-center md:gap-12 h-full min-h-0">
        {/* PM Polyhedron — hero sized, sticky */}
        <div className="flex shrink-0 flex-col items-center gap-3 md:sticky md:top-1/2 md:-translate-y-1/2 md:self-center">
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
        <div className="min-w-0 flex-1 h-full flex flex-col min-h-0">
          <AnimatePresence mode="wait">
            {status === "opening_message" && (
              <motion.div key="opening" className="flex flex-col min-h-0 flex-1">
                <PhaseReviewMessageCard
                  content={openingContent || openingMessage}
                  isStreaming={pmState === "active"}
                  showContinue={true}
                  onContinue={handleOpeningContinue}
                />
              </motion.div>
            )}

            {status === "artifact_review" && (
              <motion.div key="artifacts" className="flex flex-col min-h-0 flex-1">
                <PhaseReviewArtifactView
                  projectId={projectId}
                  phaseName={currentPhase || "Current"}
                  phaseSummaryPath={phaseSummaryPath}
                  artifacts={artifacts}
                  chatHistory={chatHistory}
                  currentChatContent={currentChatContent}
                  isChatStreaming={isChatStreaming}
                  onSendMessage={handleSendChatMessage}
                  onApprove={handleApprove}
                  isLoading={isLoading}
                />
              </motion.div>
            )}

            {status === "closing_message" && (
              <motion.div key="closing" className="flex flex-col min-h-0 flex-1">
                <PhaseReviewMessageCard
                  content={closingContent || closingMessage}
                  isStreaming={pmState === "active"}
                  showContinue={true}
                  onContinue={handleClosingContinue}
                />
              </motion.div>
            )}

            {status === "closing_complete" && (
              <motion.div key="closing-continue" className="flex flex-col min-h-0 flex-1 justify-center">
                <div className="flex flex-col gap-4 items-center text-center">
                  <h2 className="text-2xl font-bold">Begin Next Phase</h2>
                  <p className="text-muted-foreground max-w-sm">
                    The {currentPhase} phase has been approved. Click below to start work on the next phase.
                  </p>
                  <Button
                    onClick={handleStartNextPhase}
                    size="lg"
                    className="mt-4"
                  >
                    Start Next Phase
                  </Button>
                </div>
              </motion.div>
            )}

          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
