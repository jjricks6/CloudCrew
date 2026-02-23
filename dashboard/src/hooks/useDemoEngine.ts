/**
 * Unified demo engine — runs in AppLayout, drives the full demo lifecycle
 * from onboarding through all project phases to engagement completion.
 *
 * The engine is a generic playbook player: it reads PhasePlaybook arrays from
 * `demoTimeline.ts` and schedules them through `agentStore.addEvent()`.
 * Onboarding questions are streamed through `onboardingStore`.
 *
 * Flow:
 *   mount → ONBOARDING (stream questions, SOW review, wrapup)
 *   → for each PhasePlaybook:
 *       workSegment → [interrupt if defined] → resumeSegment → approval
 *   → ENGAGEMENT COMPLETE (PM streams closing message)
 *
 * Phase-jump controls (Restart / Rewind / Fast Forward) are handled via
 * `demoControlStore`. The engine subscribes and applies checkpoints.
 */

import { useEffect, useRef } from "react";
import { chunkText, isDemoMode, advanceDemoPhase, DEMO_PROJECT_STATUS } from "@/lib/demo";
import { useAgentStore } from "@/state/stores/agentStore";
import { useOnboardingStore } from "@/state/stores/onboardingStore";
import { usePhaseReviewStore } from "@/state/stores/phaseReviewStore";
import {
  useDemoControlStore,
  type DemoPhase,
} from "@/state/stores/demoControlStore";
import { applyCheckpoint } from "@/lib/demoCheckpoints";
import { PHASE_PLAYBOOKS, type PhasePlaybook, type TimelineStep } from "@/lib/demoTimeline";
import {
  ONBOARDING_STEPS,
  REVISION_STEP,
  WRAPUP_MESSAGE,
  DEMO_SOW_CONTENT,
} from "@/lib/onboardingDemoTimeline";
import { queryClient } from "@/state/queryClient";

// ---------------------------------------------------------------------------
// Engine phase → demo phase mapping
// ---------------------------------------------------------------------------

type EnginePhase =
  | "onboarding"
  | "onboarding_sow"
  | "onboarding_wrapup"
  | "phase_work"
  | "phase_interrupt"
  | "phase_resume"
  | "phase_approval"
  | "complete"
  | "done";

/** Map playbook phase name to DemoPhase for control store. */
function playbookToDemoPhase(playbookPhase: string): DemoPhase {
  switch (playbookPhase) {
    case "ARCHITECTURE": return "architecture";
    case "POC": return "poc";
    case "PRODUCTION": return "production";
    case "HANDOFF": return "handoff";
    default: return "architecture";
  }
}

/** Find the first agent with an agent_active event in a timeline segment. */
function firstActiveAgent(steps: TimelineStep[]): string {
  for (const step of steps) {
    if (step.event.event === "agent_active") return step.event.agent_name;
  }
  return "Solutions Architect";
}

/** Find the last agent with an agent_active event in a timeline segment. */
function lastActiveAgent(steps: TimelineStep[]): string {
  for (let i = steps.length - 1; i >= 0; i--) {
    const evt = steps[i].event;
    if (evt.event === "agent_active") return evt.agent_name;
  }
  return "Solutions Architect";
}

/** Get the agent that should hand off to PM before an interrupt or approval. */
function handoffAgent(playbook: PhasePlaybook, segment: "work" | "resume"): string {
  const steps = segment === "work" ? playbook.workSegment : playbook.resumeSegment;
  return lastActiveAgent(steps.length > 0 ? steps : playbook.workSegment);
}

/** Closing PM message streamed after all phases are done. */
const COMPLETION_MESSAGE =
  "Congratulations — the **E-Commerce Platform Migration** engagement is officially complete! 🎉\n\n" +
  "Here's a summary of what your CloudCrew team delivered:\n\n" +
  "**Architecture** — Serverless design with API Gateway, Lambda, and DynamoDB. " +
  "Full ADR documentation and security review.\n\n" +
  "**Proof of Concept** — Working auth integration, load-tested at 2x expected traffic, " +
  "security-scanned with zero critical findings.\n\n" +
  "**Production** — Blue-green deployment live, 2.8M records migrated with zero data loss, " +
  "all 287 regression tests passing.\n\n" +
  "**Handoff** — Operations runbook, API documentation, training materials, and PCI-DSS " +
  "compliance report all delivered. Three knowledge transfer sessions completed.\n\n" +
  "All artifacts are available in the **Artifacts** tab. If you need anything " +
  "in the future, your team's knowledge base is preserved and searchable.\n\n" +
  "It's been a pleasure working with you. How did we do? I'd love your feedback " +
  "on the engagement — what went well and what could we improve for next time?";

export function useDemoEngine(projectId: string | undefined) {
  const timeoutsRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const intervalsRef = useRef<ReturnType<typeof setInterval>[]>([]);
  const enginePhaseRef = useRef<EnginePhase>("onboarding");
  /** Which playbook in PHASE_PLAYBOOKS we're currently executing. */
  const playbookIndexRef = useRef(0);

  useEffect(() => {
    if (!isDemoMode(projectId)) return;

    const addEvent = useAgentStore.getState().addEvent;

    // ── Scheduling helpers ────────────────────────────────────────────

    function setEnginePhase(phase: EnginePhase) {
      enginePhaseRef.current = phase;
    }

    /** Sync the user-facing demo phase indicator. */
    function syncDemoPhase(dp: DemoPhase) {
      useDemoControlStore.getState().setCurrentPhase(dp);
    }

    function schedule(fn: () => void, ms: number) {
      const t = setTimeout(fn, ms);
      timeoutsRef.current.push(t);
      return t;
    }

    function cancelAll() {
      for (const t of timeoutsRef.current) clearTimeout(t);
      timeoutsRef.current = [];
      for (const i of intervalsRef.current) clearInterval(i);
      intervalsRef.current = [];
    }

    function playSegment(steps: TimelineStep[], onComplete?: () => void): number {
      let cumulative = 0;
      for (const step of steps) {
        cumulative += step.delayMs;
        const event = step.event;
        schedule(() => addEvent(event), cumulative);
      }
      if (onComplete) schedule(onComplete, cumulative + 100);
      return cumulative;
    }

    function streamQuestion(questionText: string, onComplete: () => void) {
      useOnboardingStore.getState().setPmState("active");
      const thinkingDelay = 500 + Math.random() * 500;
      schedule(() => {
        const chunks = chunkText(questionText);
        let i = 0;
        const interval = setInterval(() => {
          if (i < chunks.length) {
            useOnboardingStore.getState().appendQuestionChunk(chunks[i]);
            i++;
          } else {
            clearInterval(interval);
            useOnboardingStore.getState().setPmState("thinking");
            onComplete();
          }
        }, 20 + Math.random() * 25);
        intervalsRef.current.push(interval);
      }, thinkingDelay);
    }

    /**
     * Stream a PM chat message using the chat_thinking → chat_chunk → chat_done
     * event sequence (same path as real WebSocket messages).
     */
    function streamChatMessage(text: string, onComplete?: () => void) {
      const phase = DEMO_PROJECT_STATUS.current_phase;
      addEvent({ event: "chat_thinking", project_id: "demo", phase });

      const thinkingDelay = 800 + Math.random() * 700;
      schedule(() => {
        const chunks = chunkText(text);
        let i = 0;
        const interval = setInterval(() => {
          if (i < chunks.length) {
            addEvent({ event: "chat_chunk", project_id: "demo", phase, content: chunks[i] });
            i++;
          } else {
            clearInterval(interval);
            const messageId = `demo-${crypto.randomUUID()}`;
            addEvent({ event: "chat_done", project_id: "demo", phase, message_id: messageId });
            if (onComplete) onComplete();
          }
        }, 20 + Math.random() * 30);
        intervalsRef.current.push(interval);
      }, thinkingDelay);
    }

    /**
     * Stream phase review steps one at a time.
     * User is guided through each step and can add comments before proceeding.
     */
    function streamPhaseReviewSteps(phaseName: string, steps: ReturnType<typeof usePhaseReviewStore.getState>["steps"]) {
      usePhaseReviewStore.getState().beginReview(phaseName, steps);
      // Start streaming the first step's content
      streamCurrentReviewStep();
    }

    /**
     * Stream the content of the current review step.
     * Called when the step is first displayed and when user clicks Continue.
     */
    function streamCurrentReviewStep() {
      const store = usePhaseReviewStore.getState();
      const currentStep = store.steps[store.currentStepIndex];

      if (!currentStep) return;

      // Reset content and set PM to active
      usePhaseReviewStore.getState().setFullStepContent("");
      usePhaseReviewStore.getState().setPmState("active");

      const thinkingDelay = 300 + Math.random() * 300;
      schedule(() => {
        const chunks = chunkText(currentStep.content);
        let i = 0;

        const interval = setInterval(() => {
          if (i < chunks.length) {
            usePhaseReviewStore.getState().appendStepChunk(chunks[i]);
            i++;
          } else {
            clearInterval(interval);
            usePhaseReviewStore.getState().setPmState("thinking");
          }
        }, 20 + Math.random() * 25);
        intervalsRef.current.push(interval);
      }, thinkingDelay);
    }

    // ── Playbook execution ────────────────────────────────────────────

    /**
     * Start executing a playbook's work segment. When complete, if the
     * playbook has an interrupt it fires it; otherwise goes straight to
     * resume + approval.
     */
    function startPlaybook(index: number) {
      playbookIndexRef.current = index;
      const playbook = PHASE_PLAYBOOKS[index];
      if (!playbook) {
        startCompletion();
        return;
      }

      const dp = playbookToDemoPhase(playbook.phase);
      syncDemoPhase(dp);

      // Set project to this phase
      DEMO_PROJECT_STATUS.current_phase = playbook.phase as typeof DEMO_PROJECT_STATUS.current_phase;
      DEMO_PROJECT_STATUS.phase_status = "IN_PROGRESS";
      void queryClient.invalidateQueries({ queryKey: ["project"] });

      setEnginePhase("phase_work");

      const leadAgent = firstActiveAgent(playbook.workSegment);

      // Every phase starts with PM kicking off, then handing off to the
      // first specialist — matching real Swarm behavior (one agent at a time).
      addEvent({
        event: "agent_active",
        project_id: "demo",
        phase: playbook.phase,
        agent_name: "Project Manager",
        detail: `Kicking off the ${playbook.phase} phase`,
      });

      if (index > 0) {
        addEvent({
          event: "phase_started",
          project_id: "demo",
          phase: playbook.phase,
          detail: `${playbook.phase} phase started`,
        });
      }

      schedule(() => {
        addEvent({
          event: "handoff",
          project_id: "demo",
          phase: playbook.phase,
          agent_name: leadAgent,
          detail: `Handoff from Project Manager to ${leadAgent}`,
        });
        schedule(() => {
          playWorkSegment(index);
        }, 2000);
      }, 2000);
    }

    function playWorkSegment(index: number) {
      const playbook = PHASE_PLAYBOOKS[index];
      if (!playbook) return;

      playSegment(playbook.workSegment, () => {
        if (playbook.interrupt) {
          fireInterrupt(index);
        } else {
          // No interrupt — go straight to approval
          startApproval(index);
        }
      });
    }

    function fireInterrupt(index: number) {
      const playbook = PHASE_PLAYBOOKS[index];
      if (!playbook?.interrupt) return;

      setEnginePhase("phase_interrupt");
      const { id, question } = playbook.interrupt;
      const fromAgent = handoffAgent(playbook, "work");

      // Last active agent → PM handoff → PM raises interrupt
      addEvent({
        event: "handoff",
        project_id: "demo",
        phase: playbook.phase,
        agent_name: "Project Manager",
        detail: `Handoff from ${fromAgent} to Project Manager`,
      });

      schedule(() => {
        addEvent({
          event: "agent_active",
          project_id: "demo",
          phase: playbook.phase,
          agent_name: "Project Manager",
          detail: "Preparing question for customer",
        });

        schedule(() => {
          addEvent({
            event: "interrupt_raised",
            project_id: "demo",
            phase: playbook.phase,
            interrupt_id: id,
            question,
          });
          addEvent({
            event: "agent_active",
            project_id: "demo",
            phase: playbook.phase,
            agent_name: "Project Manager",
            detail: "Waiting for customer response",
          });

          // Also post the question as a chat message so it appears in chat
          schedule(() => {
            addEvent({
              event: "chat_message",
              project_id: "demo",
              phase: playbook.phase,
              message_id: `interrupt-${id}`,
              role: "pm",
              content: question,
            });
          }, 100);
        }, 1500);
      }, 2000);
    }

    function startResume(index: number) {
      const playbook = PHASE_PLAYBOOKS[index];
      if (!playbook) return;

      setEnginePhase("phase_resume");
      playSegment(playbook.resumeSegment, () => {
        startApproval(index);
      });
    }

    function startApproval(index: number) {
      const playbook = PHASE_PLAYBOOKS[index];
      if (!playbook) return;

      setEnginePhase("phase_approval");
      const fromAgent = handoffAgent(playbook, "resume");

      // Last active agent → PM handoff → PM requests approval
      addEvent({
        event: "handoff",
        project_id: "demo",
        phase: playbook.phase,
        agent_name: "Project Manager",
        detail: `Handoff from ${fromAgent} to Project Manager`,
      });

      schedule(() => {
        addEvent({
          event: "agent_active",
          project_id: "demo",
          phase: playbook.phase,
          agent_name: "Project Manager",
          detail: "All deliverables validated — requesting customer approval",
        });

        schedule(() => {
          addEvent({
            event: "awaiting_approval",
            project_id: "demo",
            phase: playbook.phase,
            detail: `${playbook.phase} phase ready for review`,
          });
          addEvent({
            event: "agent_active",
            project_id: "demo",
            phase: playbook.phase,
            agent_name: "Project Manager",
            detail: "Waiting for customer to review deliverables",
          });

          // Stream phase review steps to the phase review store
          schedule(() => {
            streamPhaseReviewSteps(playbook.phase, playbook.reviewSteps);
            // After review is set up, add the approval question to chat
            addEvent({
              event: "chat_message",
              project_id: "demo",
              phase: playbook.phase,
              message_id: `approval-${playbook.phase}`,
              role: "pm",
              content: playbook.approvalQuestion,
            });
          }, 100);
        }, 1500);
      }, 2000);
    }

    /** Advance to next playbook or start completion with smooth transition. */
    function advanceToNextPlaybook() {
      const nextIndex = playbookIndexRef.current + 1;

      // 1. Fade all agents to idle — Framer Motion spring animation (~500ms)
      useAgentStore.setState({
        agents: useAgentStore.getState().agents.map((a) => ({
          ...a,
          status: "idle" as const,
          detail: "",
        })),
      });

      // 2. After agents fade, advance the demo phase (progress bar fills)
      schedule(() => {
        advanceDemoPhase();
        void queryClient.invalidateQueries({ queryKey: ["project"] });

        // 3. After progress bar fills, start the next playbook (or completion)
        schedule(() => {
          if (nextIndex < PHASE_PLAYBOOKS.length) {
            startPlaybook(nextIndex);
          } else {
            startCompletion();
          }
        }, 800);
      }, 800);
    }

    /** Engagement complete — PM streams closing message. */
    function startCompletion() {
      setEnginePhase("complete");
      syncDemoPhase("complete");

      // Set all agents to idle except PM
      useAgentStore.getState().reset();
      useAgentStore.setState({
        agents: [{
          agent_name: "Project Manager",
          status: "active",
          phase: "HANDOFF",
          detail: "Presenting final engagement summary",
          timestamp: Date.now(),
        }],
        wsStatus: "connected",
      });

      streamChatMessage(COMPLETION_MESSAGE, () => {
        setEnginePhase("done");
        useAgentStore.setState({
          agents: [{
            agent_name: "Project Manager",
            status: "idle",
            phase: "HANDOFF",
            detail: "Engagement complete",
            timestamp: Date.now(),
          }],
        });
      });
    }

    // ── Start the project phase demo (all playbooks) ──────────────────

    function startProjectDemo() {
      startPlaybook(0);
    }

    // ── Onboarding ────────────────────────────────────────────────────

    function startOnboarding() {
      setEnginePhase("onboarding");
      syncDemoPhase("onboarding");
      const status = useOnboardingStore.getState().status;
      if (status === "not_started") {
        useOnboardingStore.getState().start();
      }
      const currentStep = useOnboardingStore.getState().currentStep;
      const firstStep = ONBOARDING_STEPS[currentStep];
      if (firstStep) {
        streamQuestion(firstStep.question, () => {
          // Ready for user input
        });
      }
    }

    // ── Determine starting point ──────────────────────────────────────

    const initialStatus = useOnboardingStore.getState().status;
    if (initialStatus === "completed") {
      startProjectDemo();
    } else {
      startOnboarding();
    }

    // ── Subscriptions ─────────────────────────────────────────────────

    // Onboarding store: react to user answers and SOW acceptance
    const unsubOnboarding = useOnboardingStore.subscribe(
      (state, prevState) => {
        // User answered a step → stream next question (or generate SOW)
        if (
          enginePhaseRef.current === "onboarding" &&
          state.currentStep > prevState.currentStep
        ) {
          cancelAll();

          // Revision answer → go straight back to SOW review
          if (state.isRevision) {
            schedule(() => {
              setEnginePhase("onboarding_sow");
              useOnboardingStore.getState().enterSowReview(DEMO_SOW_CONTENT);
            }, 800);
            return;
          }

          const nextStep = state.currentStep;
          const nextQuestion = ONBOARDING_STEPS[nextStep];
          if (!nextQuestion) return;
          const isLastStep = nextStep >= ONBOARDING_STEPS.length - 1;

          if (isLastStep) {
            streamQuestion(nextQuestion.question, () => {
              schedule(() => {
                setEnginePhase("onboarding_sow");
                useOnboardingStore.getState().enterSowReview(DEMO_SOW_CONTENT);
              }, 1500);
            });
          } else {
            streamQuestion(nextQuestion.question, () => {
              // Ready for next user input
            });
          }
        }

        // User accepted SOW → stream wrap-up message
        if (
          prevState.status === "sow_review" &&
          state.status === "wrapup" &&
          enginePhaseRef.current === "onboarding_sow"
        ) {
          cancelAll();
          setEnginePhase("onboarding_wrapup");
          streamQuestion(WRAPUP_MESSAGE, () => {
            // Waiting for user to click "Continue to Dashboard"
          });
        }

        // User clicked "Continue to Dashboard" → start project demo.
        // Guard on engine phase so checkpoint resets (which call .complete()
        // programmatically) don't accidentally trigger startProjectDemo().
        if (
          prevState.status !== "completed" &&
          state.status === "completed" &&
          enginePhaseRef.current.startsWith("onboarding")
        ) {
          cancelAll();
          schedule(() => startProjectDemo(), 800);
        }

        // User requested SOW revision → ask what they want changed
        if (
          prevState.status === "sow_review" &&
          state.status === "in_progress" &&
          state.isRevision &&
          enginePhaseRef.current === "onboarding_sow"
        ) {
          cancelAll();
          setEnginePhase("onboarding");
          streamQuestion(REVISION_STEP.question, () => {
            // Ready for user input
          });
        }
      },
    );

    // Agent store: react to interrupt/approval dismissals
    const unsubAgent = useAgentStore.subscribe((state, prevState) => {
      // User answered interrupt → play resume segment
      if (
        prevState.pendingInterrupt !== null &&
        state.pendingInterrupt === null &&
        enginePhaseRef.current === "phase_interrupt"
      ) {
        cancelAll();
        startResume(playbookIndexRef.current);
      }

      // User approved phase → advance to next playbook
      if (
        prevState.pendingApproval !== null &&
        state.pendingApproval === null &&
        enginePhaseRef.current === "phase_approval"
      ) {
        cancelAll();
        advanceToNextPlaybook();
      }
    });

    // Demo control store: react to phase-jump requests
    const unsubControl = useDemoControlStore.subscribe(
      (state, prevState) => {
        if (
          state.jumpTarget !== null &&
          state.jumpTarget !== prevState.jumpTarget
        ) {
          const target = state.jumpTarget;
          useDemoControlStore.getState().clearJump();
          cancelAll();
          // Neutralize engine phase BEFORE resetting stores. Otherwise the
          // agent-store subscription sees pendingInterrupt/pendingApproval go
          // null and interprets it as "user answered" — triggering a stale
          // startResume() or advanceToNextPlaybook() for the old playbook.
          setEnginePhase("done");
          applyCheckpoint(target);

          switch (target) {
            case "onboarding":
              startOnboarding();
              break;
            case "architecture":
              startPlaybook(0);
              break;
            case "poc":
              startPlaybook(1);
              break;
            case "production":
              startPlaybook(2);
              break;
            case "handoff":
              startPlaybook(3);
              break;
            case "complete":
              startCompletion();
              break;
          }
        }
      },
    );

    // Subscribe to phase review store to stream content when steps change
    const unsubPhaseReview = usePhaseReviewStore.subscribe((state, prevState) => {
      // When review starts (status changes to reviewing), stream first step
      if (
        (prevState.status === "not_started" || prevState.status === "waiting_to_start") &&
        state.status === "reviewing"
      ) {
        cancelAll();
        streamCurrentReviewStep();
        return;
      }

      // When user advances to next step, stream the new step's content
      if (
        state.status === "reviewing" &&
        state.currentStepIndex > prevState.currentStepIndex
      ) {
        cancelAll();
        streamCurrentReviewStep();
      }
    });

    return () => {
      cancelAll();
      unsubOnboarding();
      unsubAgent();
      unsubControl();
      unsubPhaseReview();
      enginePhaseRef.current = "onboarding";
    };
  }, [projectId]);
}
