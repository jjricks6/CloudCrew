/**
 * Zustand store for agent activity and WebSocket connection state.
 *
 * Populated by incoming WebSocket events via useCloudCrewSocket.
 */

import { create } from "zustand";
import type { AgentActivity, WebSocketEvent, WsStatus } from "@/lib/types";

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

      // For other event types, just update lastEvent
      return { lastEvent: event };
    }),

  reset: () => set({ agents: [], wsStatus: "disconnected", lastEvent: null }),
}));
