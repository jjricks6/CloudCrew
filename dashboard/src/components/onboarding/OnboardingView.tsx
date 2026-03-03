/**
 * Onboarding view — PM polyhedron hero on the left, question card on the right.
 *
 * This replaces the normal DashboardPage content when onboarding is not yet
 * complete. The PM agent guides the user through project setup one question
 * at a time, culminating in a SOW review and approval.
 *
 * Supports two modes:
 *   - Demo mode: scripted ONBOARDING_STEPS driven by useDemoEngine
 *   - Real mode: dynamic PM questions arriving via WebSocket interrupts
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

import { useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AgentPolyhedron } from "@/components/swarm/AgentPolyhedron";
import { AGENT_CONFIG } from "@/components/swarm/swarm-constants";
import { OnboardingQuestionCard } from "./OnboardingQuestionCard";
import { SowReviewCard } from "./SowReviewCard";
import { WrapupCard } from "./WrapupCard";
import { useOnboardingStore } from "@/state/stores/onboardingStore";
import { useAgentStore } from "@/state/stores/agentStore";
import { useRespondToInterrupt } from "@/state/queries/useApprovalQueries";
import { useProjectId } from "@/lib/useProjectId";
import { ONBOARDING_STEPS, REVISION_STEP } from "@/lib/onboardingDemoTimeline";
import type { OnboardingStep } from "@/lib/onboardingDemoTimeline";

const PM_CONFIG = AGENT_CONFIG["Project Manager"];

export function OnboardingView() {
  const status = useOnboardingStore((s) => s.status);
  const currentStep = useOnboardingStore((s) => s.currentStep);
  const pmState = useOnboardingStore((s) => s.pmState);
  const questionText = useOnboardingStore((s) => s.currentQuestionText);
  const sowContent = useOnboardingStore((s) => s.sowContent);
  const isRevision = useOnboardingStore((s) => s.isRevision);
  const isRealMode = useOnboardingStore((s) => s.isRealMode);
  const liveInterruptId = useOnboardingStore((s) => s.liveInterruptId);
  const thinkingMessage = useOnboardingStore((s) => s.thinkingMessage);
  const questionsAnswered = useOnboardingStore((s) => s.questionsAnswered);

  const projectId = useProjectId();
  const respondToInterrupt = useRespondToInterrupt(projectId);

  const isStreaming = pmState === "active";
  const isThinking = pmState === "thinking";

  // Build step: dynamic from interrupt in real mode, scripted in demo
  let step: OnboardingStep | null;
  if (isRealMode) {
    step = questionText
      ? {
          question: questionText,
          placeholder: "Type your response...",
          allowUpload: false,
          demoAnswer: "",
        }
      : null;
  } else {
    step = isRevision
      ? REVISION_STEP
      : ONBOARDING_STEPS[currentStep] ?? null;
  }

  // Real-mode answer handler — sends response to backend interrupt API
  const handleRealSend = useCallback(
    (answer: string) => {
      if (!liveInterruptId) return;
      respondToInterrupt.mutate({
        interruptId: liveInterruptId,
        response: answer,
      });
      // Show PM thinking while waiting for next question
      useOnboardingStore.getState().setPmState("thinking");
      useOnboardingStore.getState().setFullQuestion("");
      useOnboardingStore.getState().setThinkingMessage("Thinking");
      const store = useOnboardingStore.getState();
      useOnboardingStore.setState({ questionsAnswered: store.questionsAnswered + 1 });
      useAgentStore.getState().dismissInterrupt();
    },
    [liveInterruptId, respondToInterrupt],
  );

  // Real-mode SOW accept handler
  const handleSowAccept = useCallback(() => {
    if (!isRealMode) return;
    const id = useOnboardingStore.getState().liveInterruptId;
    if (!id) return;
    respondToInterrupt.mutate({ interruptId: id, response: "Approved" });
    useOnboardingStore.getState().setPmState("thinking");
    useOnboardingStore.getState().setThinkingMessage("Finalizing project setup");
    useOnboardingStore.getState().setFullQuestion("");
    useOnboardingStore.setState({ status: "in_progress", questionsAnswered: useOnboardingStore.getState().questionsAnswered + 1 });
    useAgentStore.getState().dismissInterrupt();
  }, [isRealMode, respondToInterrupt]);

  // Real-mode SOW revision handler
  const handleSowRevise = useCallback(() => {
    if (!isRealMode) return;
    useOnboardingStore.getState().requestRevision();
  }, [isRealMode]);

  // Real-mode SOW revision submit (user types feedback then sends)
  const handleRevisionSend = useCallback(
    (feedback: string) => {
      const id = useOnboardingStore.getState().liveInterruptId;
      if (!id) return;
      respondToInterrupt.mutate({ interruptId: id, response: feedback });
      useOnboardingStore.getState().setPmState("thinking");
      useOnboardingStore.getState().setFullQuestion("");
      useOnboardingStore.getState().setThinkingMessage("Incorporating your feedback");
      const store = useOnboardingStore.getState();
      useOnboardingStore.setState({ questionsAnswered: store.questionsAnswered + 1 });
      useAgentStore.getState().dismissInterrupt();
    },
    [respondToInterrupt],
  );

  // Determine thinking display text
  const thinkingDisplay =
    questionsAnswered === 0 && thinkingMessage === "Analyzing your project details and preparing questions"
      ? thinkingMessage
      : thinkingMessage || "Thinking";

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

        {/* Question / SOW review / thinking state */}
        <div className="min-w-0 flex-1">
          <AnimatePresence mode="wait">
            {/* Real mode: PM is thinking (between questions or generating SOW) */}
            {isRealMode && !step && isThinking && status === "in_progress" && (
              <motion.div
                key="pm-thinking"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -12 }}
                transition={{ duration: 0.4, ease: "easeOut" }}
              >
                <div className="flex flex-col gap-3">
                  <div className="text-base leading-relaxed text-foreground">
                    {thinkingDisplay}
                    <span className="ml-1 inline-flex gap-0.5">
                      <span className="animate-bounce" style={{ animationDelay: "0ms" }}>.</span>
                      <span className="animate-bounce" style={{ animationDelay: "150ms" }}>.</span>
                      <span className="animate-bounce" style={{ animationDelay: "300ms" }}>.</span>
                    </span>
                  </div>
                  {questionsAnswered === 0 && (
                    <p className="text-sm text-muted-foreground">
                      I&apos;m reviewing the requirements you provided and will have a few
                      clarifying questions to make sure we build exactly what you need.
                    </p>
                  )}
                  {thinkingDisplay.toLowerCase().includes("statement of work") && (
                    <p className="text-sm text-muted-foreground">
                      This may take a couple of minutes. The PM is drafting a detailed
                      scope, timeline, and deliverables based on your answers.
                    </p>
                  )}
                </div>
              </motion.div>
            )}

            {status === "wrapup" ? (
              <motion.div key="wrapup">
                <WrapupCard
                  messageText={questionText}
                  isStreaming={isStreaming}
                />
              </motion.div>
            ) : status === "sow_review" ? (
              <motion.div key="sow">
                <SowReviewCard
                  sowContent={sowContent}
                  onAccept={isRealMode ? handleSowAccept : undefined}
                  onRevise={isRealMode ? handleSowRevise : undefined}
                />
              </motion.div>
            ) : step ? (
              <motion.div
                key={
                  isRealMode
                    ? `live-${liveInterruptId}`
                    : isRevision
                      ? "revision"
                      : `step-${currentStep}`
                }
              >
                <OnboardingQuestionCard
                  step={step}
                  questionText={questionText}
                  isStreaming={isStreaming}
                  onSend={
                    isRealMode
                      ? isRevision
                        ? handleRevisionSend
                        : handleRealSend
                      : undefined
                  }
                />
              </motion.div>
            ) : null}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
