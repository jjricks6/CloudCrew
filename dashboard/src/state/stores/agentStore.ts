/**
 * Zustand store for agent activity and WebSocket connection state.
 *
 * Populated by incoming WebSocket events via useCloudCrewSocket.
 */

import { create } from "zustand";
import type { AgentActivity, WebSocketEvent, WsStatus } from "@/lib/types";
import { queryClient } from "@/state/queryClient";
import { useChatStore } from "./chatStore";

interface AgentState {
  agents: AgentActivity[];
  wsStatus: WsStatus;
  lastEvent: WebSocketEvent | null;

  setWsStatus: (status: WsStatus) => void;
  addEvent: (event: WebSocketEvent) => void;
  reset: () => void;
}

export const useAgentStore = create<AgentState>((set) => ({
  agents: [],
  wsStatus: "disconnected",
  lastEvent: null,

  setWsStatus: (status) => set({ wsStatus: status }),

  addEvent: (event) =>
    set((state) => {
      const now = Date.now();

      if (event.event === "agent_active") {
        const existing = state.agents.find(
          (a) => a.agent_name === event.agent_name,
        );
        if (existing) {
          return {
            lastEvent: event,
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
          lastEvent: event,
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
        return {
          lastEvent: event,
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

      // Chat events → dispatch to chatStore
      if (event.event === "chat_message") {
        // Customer messages are added optimistically by ChatPage on send,
        // so only add PM messages arriving via WebSocket to avoid duplicates.
        if (event.role === "pm") {
          useChatStore.getState().addMessage({
            message_id: event.message_id,
            role: event.role,
            content: event.content,
            timestamp: new Date().toISOString(),
          });
        }
        return { lastEvent: event };
      }

      if (event.event === "chat_thinking") {
        useChatStore.getState().setThinking(true);
        return { lastEvent: event };
      }

      if (event.event === "chat_chunk") {
        useChatStore.getState().appendChunk(event.content);
        return { lastEvent: event };
      }

      if (event.event === "chat_done") {
        useChatStore.getState().finalizeStream(event.message_id);
        return { lastEvent: event };
      }

      // Board task events → invalidate board-tasks query
      if (event.event === "task_created" || event.event === "task_updated") {
        void queryClient.invalidateQueries({ queryKey: ["board-tasks"] });
        return { lastEvent: event };
      }

      // Phase events → invalidate project query
      if (
        event.event === "phase_started" ||
        event.event === "awaiting_approval"
      ) {
        void queryClient.invalidateQueries({ queryKey: ["project"] });
        return { lastEvent: event };
      }

      // For other event types, just update lastEvent
      return { lastEvent: event };
    }),

  reset: () => set({ agents: [], wsStatus: "disconnected", lastEvent: null }),
}));
