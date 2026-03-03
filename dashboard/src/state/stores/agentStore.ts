/**
 * Zustand store for agent activity and WebSocket connection state.
 *
 * Populated by incoming WebSocket events via useCloudCrewSocket.
 */

import { create } from "zustand";
import type {
  AgentActivity,
  SwarmTimelineEvent,
  WebSocketEvent,
  WsStatus,
} from "@/lib/types";
import { queryClient } from "@/state/queryClient";
import { useChatStore } from "./chatStore";
import { useOnboardingStore } from "./onboardingStore";
import { usePhaseReviewStore } from "./phaseReviewStore";
import {
  isDemoMode,
  setDemoAwaitingApproval,
  setDemoAwaitingInput,
  clearDemoAwaitingInput,
  clearDemoAwaitingApproval,
  updateDemoBoardTask,
  addDemoDeliverable,
} from "@/lib/demo";

interface ActiveHandoff {
  from: string;
  to: string;
  id: string;
}

interface PendingInterrupt {
  interrupt_id: string;
  question: string;
  phase: string;
  timestamp: number;
}

interface PendingApproval {
  phase: string;
  timestamp: number;
}

interface AgentState {
  agents: AgentActivity[];
  wsStatus: WsStatus;
  swarmEvents: SwarmTimelineEvent[];
  activeHandoff: ActiveHandoff | null;
  pendingInterrupt: PendingInterrupt | null;
  pendingApproval: PendingApproval | null;

  setWsStatus: (status: WsStatus) => void;
  addEvent: (event: WebSocketEvent) => void;
  clearHandoff: (id: string) => void;
  dismissInterrupt: () => void;
  dismissApproval: () => void;
  reset: () => void;
}

function makeTimelineEvent(
  type: SwarmTimelineEvent["type"],
  agentName: string,
  detail: string,
  phase: string,
  fromAgent?: string,
): SwarmTimelineEvent {
  return {
    id: crypto.randomUUID(),
    type,
    agentName,
    detail,
    phase,
    timestamp: Date.now(),
    fromAgent,
  };
}

function appendEvent(
  events: SwarmTimelineEvent[],
  event: SwarmTimelineEvent,
): SwarmTimelineEvent[] {
  return [event, ...events].slice(0, 50);
}

export const useAgentStore = create<AgentState>((set, get) => ({
  agents: [],
  wsStatus: "disconnected",
  swarmEvents: [],
  activeHandoff: null,
  pendingInterrupt: null,
  pendingApproval: null,

  setWsStatus: (status) => set({ wsStatus: status }),

  addEvent: (event) =>
    set((state) => {
      const now = Date.now();

      if (event.event === "agent_active") {
        const timelineEvent = makeTimelineEvent(
          "agent_active",
          event.agent_name,
          event.detail,
          event.phase,
        );

        // Update onboarding thinking message when PM reports activity
        const onboarding = useOnboardingStore.getState();
        if (
          onboarding.isRealMode &&
          onboarding.status === "in_progress" &&
          event.agent_name === "Project Manager" &&
          onboarding.pmState === "thinking"
        ) {
          onboarding.setThinkingMessage(event.detail);
        }

        const existing = state.agents.find(
          (a) => a.agent_name === event.agent_name,
        );
        if (existing) {
          return {
            swarmEvents: appendEvent(state.swarmEvents, timelineEvent),
            agents: state.agents.map((a) =>
              a.agent_name === event.agent_name
                ? {
                    ...a,
                    status: "active" as const,
                    detail: event.detail,
                    timestamp: now,
                  }
                : a,
            ),
          };
        }
        return {
          swarmEvents: appendEvent(state.swarmEvents, timelineEvent),
          agents: [
            ...state.agents,
            {
              agent_name: event.agent_name,
              status: "active",
              phase: event.phase,
              detail: event.detail,
              timestamp: now,
            },
          ],
        };
      }

      if (event.event === "agent_idle") {
        // Idle events update visual state only — no timeline entry.
        // The real backend fires these when agents finish; the meaningful
        // work updates come from agent_active (report_activity tool).
        return {
          agents: state.agents.map((a) =>
            a.agent_name === event.agent_name
              ? {
                  ...a,
                  status: "idle" as const,
                  detail: event.detail,
                  timestamp: now,
                }
              : a,
          ),
        };
      }

      if (event.event === "handoff") {
        // A handoff means: source agent finishes → work transfers to target.
        // This idles the source and puts the target into "thinking" (lit up,
        // pulsing, not yet spinning). The target transitions to "active"
        // once it calls report_activity (fires an agent_active event).
        const match = event.detail.match(/Handoff from (.+) to (.+)/);
        const fromAgent = match?.[1] ?? "unknown";
        const toAgent = event.agent_name;

        const handoffId = crypto.randomUUID();

        // Auto-clear handoff arc after 2 seconds. The clearHandoff action
        // checks the ID matches before clearing, so a stale timeout firing
        // after a store reset or new handoff is harmless (no-op).
        setTimeout(() => {
          get().clearHandoff(handoffId);
        }, 2000);

        const targetExists = state.agents.some(
          (a) => a.agent_name === toAgent,
        );

        let updatedAgents = state.agents.map((a) => {
          if (a.agent_name === fromAgent) {
            return { ...a, status: "idle" as const, timestamp: now };
          }
          if (a.agent_name === toAgent) {
            return { ...a, status: "thinking" as const, timestamp: now };
          }
          return a;
        });

        // If the target agent hasn't appeared yet, add it
        if (!targetExists) {
          updatedAgents = [
            ...updatedAgents,
            {
              agent_name: toAgent,
              status: "thinking" as const,
              phase: event.phase,
              detail: "",
              timestamp: now,
            },
          ];
        }

        return {
          activeHandoff: { from: fromAgent, to: toAgent, id: handoffId },
          agents: updatedAgents,
        };
      }

      // Chat events → dispatch to chatStore
      if (event.event === "chat_message") {
        if (event.role === "pm") {
          // Infer message card type from the message_id convention.
          // Centralised here so ChatMessageList uses the explicit type field.
          const msgType = event.message_id.startsWith("approval-")
            ? ("approval" as const)
            : ("chat" as const);
          useChatStore.getState().addMessage({
            message_id: event.message_id,
            role: event.role,
            content: event.content,
            timestamp: new Date().toISOString(),
            type: msgType,
          });
        }
        return {};
      }

      if (event.event === "chat_thinking") {
        const reviewStatus = usePhaseReviewStore.getState().status;
        if (reviewStatus === "artifact_review") {
          usePhaseReviewStore.getState().setPmState("active");
        } else {
          useChatStore.getState().setThinking(true);
        }
        return {};
      }

      if (event.event === "chat_chunk") {
        const reviewStatus = usePhaseReviewStore.getState().status;
        if (reviewStatus === "artifact_review") {
          usePhaseReviewStore.getState().appendChatChunk(event.content);
        } else {
          useChatStore.getState().appendChunk(event.content);
        }
        return {};
      }

      if (event.event === "chat_done") {
        const reviewStatus = usePhaseReviewStore.getState().status;
        if (reviewStatus === "artifact_review") {
          usePhaseReviewStore.getState().completeChatMessage();
        } else {
          useChatStore.getState().finalizeStream(event.message_id);
        }
        return {};
      }

      // Review message events → dispatch to phaseReviewStore
      if (event.event === "review_message") {
        usePhaseReviewStore.getState().appendMessageContent(
          event.message_type,
          event.content,
        );
        return {};
      }

      if (event.event === "review_message_thinking") {
        usePhaseReviewStore.getState().setPmState("active");
        return {};
      }

      if (event.event === "review_message_complete") {
        usePhaseReviewStore.getState().setMessageComplete(event.message_type);
        return {};
      }

      // Board task events → mutate demo data + invalidate board-tasks query
      if (event.event === "task_updated") {
        if (isDemoMode(event.project_id)) {
          updateDemoBoardTask(event.task_id, event.updates);
        }
        void queryClient.invalidateQueries({ queryKey: ["board-tasks"] });
        return {};
      }
      if (event.event === "task_created") {
        void queryClient.invalidateQueries({ queryKey: ["board-tasks"] });
        return {};
      }

      // Deliverable events → mutate demo data + invalidate deliverables query
      if (event.event === "deliverable_created") {
        if (isDemoMode(event.project_id)) {
          addDemoDeliverable(event.phase, {
            name: event.name,
            git_path: event.git_path,
            version: event.version,
            created_at: new Date().toISOString(),
          });
        }
        void queryClient.invalidateQueries({ queryKey: ["deliverables"] });
        return {};
      }

      // Phase events → invalidate project query
      if (event.event === "phase_started") {
        void queryClient.invalidateQueries({ queryKey: ["project"] });
        return {};
      }

      // Approval events → store for UI notification + invalidate project query
      if (event.event === "awaiting_approval") {
        if (isDemoMode(event.project_id)) {
          setDemoAwaitingApproval();
        }
        void queryClient.invalidateQueries({ queryKey: ["project"] });
        return {
          pendingApproval: {
            phase: event.phase,
            timestamp: now,
          },
        };
      }

      // SOW review event → show review card with embedded SOW content
      if (event.event === "sow_review") {
        void queryClient.invalidateQueries({ queryKey: ["project"] });

        const onboarding = useOnboardingStore.getState();
        if (onboarding.isRealMode && onboarding.status === "in_progress") {
          // Store the interrupt ID so accept/revise handlers can respond
          useOnboardingStore.setState({ liveInterruptId: event.interrupt_id });

          // Use SOW content from the WebSocket event (sent by ECS runner)
          if (event.sow_content) {
            useOnboardingStore.getState().enterSowReview(event.sow_content);
          } else {
            console.warn("sow_review event received without sow_content");
          }
        }

        return {
          pendingInterrupt: {
            interrupt_id: event.interrupt_id,
            question: "SOW review",
            phase: event.phase,
            timestamp: now,
          },
        };
      }

      // Interrupt events → store for UI notification + inject chat message
      if (event.event === "interrupt_raised") {
        if (isDemoMode(event.project_id)) {
          setDemoAwaitingInput();
        }
        void queryClient.invalidateQueries({ queryKey: ["project"] });

        // Route to onboarding UI if in real-mode onboarding (Discovery phase)
        const onboarding = useOnboardingStore.getState();
        if (onboarding.isRealMode && onboarding.status === "in_progress") {
          onboarding.setLiveQuestion(event.question, event.interrupt_id);
        }

        // Inject a synthetic chat message so ChatMessageList renders the
        // InterruptQuestionCard via the explicit type field.
        useChatStore.getState().addMessage({
          message_id: `interrupt-${event.interrupt_id}`,
          role: "pm",
          content: event.question,
          timestamp: new Date().toISOString(),
          type: "interrupt",
        });

        return {
          pendingInterrupt: {
            interrupt_id: event.interrupt_id,
            question: event.question,
            phase: event.phase,
            timestamp: now,
          },
        };
      }

      return {};
    }),

  clearHandoff: (id) =>
    set((state) =>
      state.activeHandoff?.id === id ? { activeHandoff: null } : {},
    ),

  dismissInterrupt: () => {
    clearDemoAwaitingInput();
    void queryClient.invalidateQueries({ queryKey: ["project"] });
    set({ pendingInterrupt: null });
  },

  dismissApproval: () => {
    clearDemoAwaitingApproval();
    void queryClient.invalidateQueries({ queryKey: ["project"] });
    set({ pendingApproval: null });
  },

  reset: () =>
    set({
      agents: [],
      wsStatus: "disconnected",
      swarmEvents: [],
      activeHandoff: null,
      pendingInterrupt: null,
      pendingApproval: null,
    }),
}));
