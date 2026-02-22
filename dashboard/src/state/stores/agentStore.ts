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
          useChatStore.getState().addMessage({
            message_id: event.message_id,
            role: event.role,
            content: event.content,
            timestamp: new Date().toISOString(),
          });
        }
        return {};
      }

      if (event.event === "chat_thinking") {
        useChatStore.getState().setThinking(true);
        return {};
      }

      if (event.event === "chat_chunk") {
        useChatStore.getState().appendChunk(event.content);
        return {};
      }

      if (event.event === "chat_done") {
        useChatStore.getState().finalizeStream(event.message_id);
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

      // Interrupt events → store for UI notification
      if (event.event === "interrupt_raised") {
        if (isDemoMode(event.project_id)) {
          setDemoAwaitingInput();
        }
        void queryClient.invalidateQueries({ queryKey: ["project"] });
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
