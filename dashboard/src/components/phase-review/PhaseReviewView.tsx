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

import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AgentPolyhedron } from "@/components/swarm/AgentPolyhedron";
import { AGENT_CONFIG, PHASE_LABELS } from "@/components/swarm/swarm-constants";
import { Button } from "@/components/ui/button";
import { Confetti } from "@/components/ui/Confetti";
import { PhaseReviewMessageCard } from "./PhaseReviewMessageCard";
import { PhaseReviewArtifactView } from "./PhaseReviewArtifactView";
import { usePhaseReviewStore } from "@/state/stores/phaseReviewStore";
import { useApprovePhase, useRevisePhase } from "@/state/queries/useApprovalQueries";
import { useProjectStatus } from "@/state/queries/useProjectQueries";
import { useProjectId } from "@/lib/useProjectId";
import { useChatStore } from "@/state/stores/chatStore";
import { useAgentStore } from "@/state/stores/agentStore";
import { isDemoMode } from "@/lib/demo";
import { useNavigate } from "react-router-dom";
import { PHASE_ORDER, type Phase } from "@/lib/types";

const PM_CONFIG = AGENT_CONFIG["Project Manager"];

export function PhaseReviewView() {
  const projectId = useProjectId();
  const navigate = useNavigate();
  const { data: project } = useProjectStatus(projectId);

  const status = usePhaseReviewStore((s) => s.status);
  const currentPhase = usePhaseReviewStore((s) => s.currentPhase);
  const pmState = usePhaseReviewStore((s) => s.pmState);

  // Opening message
  const openingMessage = usePhaseReviewStore((s) => s.openingMessage);
  const openingContent = usePhaseReviewStore((s) => s.openingContent);

  // Artifact review
  const chatHistory = usePhaseReviewStore((s) => s.chatHistory);
  const currentChatContent = usePhaseReviewStore((s) => s.currentChatContent);

  // Closing message
  const closingMessage = usePhaseReviewStore((s) => s.closingMessage);
  const closingContent = usePhaseReviewStore((s) => s.closingContent);

  const approvePhase = useApprovePhase(projectId);
  const revisePhase = useRevisePhase(projectId);

  const isLoading = approvePhase.isPending || revisePhase.isPending;
  const isChatStreaming = pmState === "active";

  // Compute human-readable next phase name for the "Begin" screen
  const currentIndex = currentPhase
    ? PHASE_ORDER.indexOf(currentPhase as Phase)
    : -1;
  const nextPhase =
    currentIndex >= 0 && currentIndex < PHASE_ORDER.length - 1
      ? PHASE_ORDER[currentIndex + 1]
      : null;
  const nextPhaseName = nextPhase ? PHASE_LABELS[nextPhase] : "Next";

  // Timeout fallback: if closing message never arrives (Lambda failure or
  // WebSocket disconnect), auto-advance after 15 seconds so the user isn't
  // stuck on a blank screen.
  const closingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (status !== "closing_message") {
      // Clear any pending timeout when we leave closing_message state
      if (closingTimeoutRef.current) {
        clearTimeout(closingTimeoutRef.current);
        closingTimeoutRef.current = null;
      }
      return;
    }

    // Only set timeout if no content has arrived yet
    const hasContent = closingContent.length > 0 || closingMessage.length > 0;
    if (hasContent) return;

    closingTimeoutRef.current = setTimeout(() => {
      const store = usePhaseReviewStore.getState();
      // Only auto-advance if we're still stuck with no content
      if (
        store.status === "closing_message" &&
        !store.closingContent &&
        !store.closingMessage
      ) {
        store.advanceFromClosing();
      }
    }, 15_000);

    return () => {
      if (closingTimeoutRef.current) {
        clearTimeout(closingTimeoutRef.current);
        closingTimeoutRef.current = null;
      }
    };
  }, [status, closingContent, closingMessage]);

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

    if (isDemoMode(projectId)) {
      // Demo: advance with static closing message from playbook
      usePhaseReviewStore.getState().advanceToClosingMessage(closingMessage);
    } else if (currentPhase === "DISCOVERY") {
      // Discovery: backend skips PM closing message generation, so go
      // directly to closing_complete and approve in one step.
      approvePhase.mutate(undefined, {
        onSuccess: () => {
          useAgentStore.getState().dismissApproval();
          usePhaseReviewStore.getState().advanceFromClosing();
        },
      });
    } else {
      // Real: advance to closing_message with empty content, then call
      // approve API. Backend triggers PM closing message via WebSocket.
      usePhaseReviewStore.getState().advanceToClosingMessage("");
      approvePhase.mutate(undefined, {
        onSuccess: () => {
          useAgentStore.getState().dismissApproval();
          // Backend will trigger PM closing message Lambda — tokens
          // stream via WebSocket into closingContent.
        },
      });
    }
  };

  const handleRequestChanges = (feedback: string) => {
    if (isDemoMode(projectId)) {
      // Demo: just exit review — demo engine handles the rest
      usePhaseReviewStore.getState().completeReview();
    } else {
      revisePhase.mutate(feedback, {
        onSuccess: () => {
          usePhaseReviewStore.getState().completeReview();
        },
      });
    }
  };

  const handleStartNextPhase = () => {
    if (isDemoMode(projectId)) {
      // Demo: approval happens here (no API call was made in handleApprove)
      approvePhase.mutate(undefined, {
        onSuccess: () => {
          useAgentStore.getState().dismissApproval();
          usePhaseReviewStore.getState().completeReview();
        },
      });
    } else {
      // Real: approval already happened in handleApprove — just complete
      usePhaseReviewStore.getState().completeReview();
    }
  };

  const handleReturnToDashboard = () => {
    usePhaseReviewStore.getState().completeReview();
    navigate(`/project/${projectId}`, { replace: true });
  };


  return (
    <div className="flex h-[calc(100dvh-10rem)] items-center justify-center overflow-x-hidden overflow-y-auto md:h-[calc(100vh-10rem)]">
      <div className="flex w-full max-w-6xl flex-col items-center gap-4 px-3 md:px-4 md:flex-row md:items-center md:gap-12 h-full min-h-0">
        {/* PM Polyhedron — hidden on mobile during artifact review to save space */}
        <div className={`flex shrink-0 flex-col items-center gap-3 md:sticky md:top-1/2 md:-translate-y-1/2 md:self-center ${status === "artifact_review" ? "hidden md:flex" : ""}`}>
          <div className="relative h-[180px] w-[180px] md:h-[260px] md:w-[260px]">
            <AgentPolyhedron
              shape={PM_CONFIG.shape}
              color={PM_CONFIG.color}
              status={pmState}
            />
            {/* PM label centered over polyhedron */}
            <span
              className="pointer-events-none absolute inset-0 flex items-center justify-center text-xl font-bold md:text-2xl"
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
        <div className="min-w-0 w-full flex-1 h-full flex flex-col min-h-0 overflow-hidden">
          <AnimatePresence mode="wait">
            {status === "opening_message" && (
              <motion.div key="opening" className="flex flex-col min-h-0 flex-1">
                <PhaseReviewMessageCard
                  content={pmState === "active" ? openingContent : (openingContent || openingMessage)}
                  isStreaming={pmState === "active"}
                  showContinue={
                    pmState !== "active" &&
                    (openingContent.length > 0 || openingMessage.length > 0)
                  }
                  onContinue={handleOpeningContinue}
                />
              </motion.div>
            )}

            {status === "artifact_review" && (
              <motion.div key="artifacts" className="flex flex-col min-h-0 flex-1">
                <PhaseReviewArtifactView
                  projectId={projectId}
                  phaseName={currentPhase || "Current"}
                  chatHistory={chatHistory}
                  currentChatContent={currentChatContent}
                  isChatStreaming={isChatStreaming}
                  onSendMessage={handleSendChatMessage}
                  onApprove={handleApprove}
                  onRequestChanges={handleRequestChanges}
                  isLoading={isLoading}
                  gitRepoUrl={project?.git_repo_url}
                />
              </motion.div>
            )}

            {status === "closing_message" && (
              <motion.div key="closing" className="flex flex-col min-h-0 flex-1">
                <PhaseReviewMessageCard
                  content={pmState === "active" ? closingContent : (closingContent || closingMessage)}
                  isStreaming={pmState === "active"}
                  showContinue={
                    pmState !== "active" &&
                    (closingContent.length > 0 || closingMessage.length > 0)
                  }
                  onContinue={handleClosingContinue}
                />
              </motion.div>
            )}

            {status === "closing_complete" && currentPhase === "HANDOFF" && (
              <motion.div
                key="engagement-complete"
                className="flex flex-col min-h-0 flex-1 justify-center"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.6 }}
              >
                <Confetti />
                <div className="flex flex-col gap-4 items-center text-center">
                  <div className="mb-6">
                    <h2 className="text-4xl font-bold bg-gradient-to-r from-yellow-400 via-pink-400 to-blue-400 bg-clip-text text-transparent mb-2">
                      Engagement Complete! 🎉
                    </h2>
                  </div>
                  <p className="text-lg text-muted-foreground max-w-md">
                    Your team is now fully equipped and confident to operate the system independently. Thank you for partnering with us on this journey!
                  </p>
                  <Button
                    onClick={handleReturnToDashboard}
                    size="lg"
                    className="mt-8"
                  >
                    Return to Dashboard
                  </Button>
                </div>
              </motion.div>
            )}

            {status === "closing_complete" && currentPhase !== "HANDOFF" && (
              <motion.div
                key="closing-continue"
                className="flex flex-col min-h-0 flex-1 justify-center"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5 }}
              >
                <div className="flex flex-col gap-4 items-center text-center">
                  <h2 className="text-2xl font-bold">
                    Begin {nextPhaseName} Phase
                  </h2>
                  <p className="text-muted-foreground max-w-sm">
                    The {currentPhase ? PHASE_LABELS[currentPhase as Phase] ?? currentPhase : "current"} phase
                    has been approved. Click below to start the {nextPhaseName} phase.
                  </p>
                  <Button
                    onClick={handleStartNextPhase}
                    size="lg"
                    className="mt-4"
                  >
                    Start {nextPhaseName} Phase
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
