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

interface AgentState {
  agents: AgentActivity[];
  wsStatus: WsStatus;
  swarmEvents: SwarmTimelineEvent[];
  activeHandoff: ActiveHandoff | null;
  pendingInterrupt: PendingInterrupt | null;

  setWsStatus: (status: WsStatus) => void;
  addEvent: (event: WebSocketEvent) => void;
  clearHandoff: (id: string) => void;
  dismissInterrupt: () => void;
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
        const timelineEvent = makeTimelineEvent(
          "agent_idle",
          event.agent_name,
          event.detail,
          event.phase,
        );
        return {
          swarmEvents: appendEvent(state.swarmEvents, timelineEvent),
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
        // Parse "Handoff from {src} to {dest}"
        const match = event.detail.match(/Handoff from (.+) to (.+)/);
        const fromAgent = match?.[1] ?? "unknown";

        const timelineEvent = makeTimelineEvent(
          "handoff",
          event.agent_name,
          event.detail,
          event.phase,
          fromAgent,
        );

        const handoffId = timelineEvent.id;

        // Auto-clear handoff after 2 seconds
        setTimeout(() => {
          get().clearHandoff(handoffId);
        }, 2000);

        // Don't update agent statuses here — the subsequent agent_active
        // and agent_idle events handle that with proper timing so the
        // source stays active (with its bubble) while the arc animates.
        return {
          activeHandoff: { from: fromAgent, to: event.agent_name, id: handoffId },
          swarmEvents: appendEvent(state.swarmEvents, timelineEvent),
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

      // Board task events → invalidate board-tasks query
      if (event.event === "task_created" || event.event === "task_updated") {
        void queryClient.invalidateQueries({ queryKey: ["board-tasks"] });
        return {};
      }

      // Phase events → invalidate project query
      if (
        event.event === "phase_started" ||
        event.event === "awaiting_approval"
      ) {
        void queryClient.invalidateQueries({ queryKey: ["project"] });
        return {};
      }

      // Interrupt events → store for UI notification
      if (event.event === "interrupt_raised") {
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

  dismissInterrupt: () => set({ pendingInterrupt: null }),

  reset: () =>
    set({
      agents: [],
      wsStatus: "disconnected",
      swarmEvents: [],
      activeHandoff: null,
      pendingInterrupt: null,
    }),
}));
