/**
 * TanStack Query hooks for PM chat.
 *
 * In demo mode, returns mock data and simulates PM streaming responses
 * without hitting the backend API.
 */

import { useMutation, useQuery } from "@tanstack/react-query";
import { get, post } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";
import { useChatStore } from "@/state/stores/chatStore";
import { useAgentStore } from "@/state/stores/agentStore";
import {
  isDemoMode,
  DEMO_CHAT_HISTORY,
  simulatePmResponse,
} from "@/lib/demo";

interface ChatHistoryResponse {
  project_id: string;
  messages: ChatMessage[];
}

interface SendMessageResponse {
  message_id: string;
}

export function useChatHistory(projectId: string | undefined) {
  return useQuery({
    queryKey: ["chat", projectId],
    queryFn: async () => {
      if (isDemoMode(projectId)) {
        useChatStore.getState().loadHistory(DEMO_CHAT_HISTORY);
        return { project_id: "demo", messages: DEMO_CHAT_HISTORY };
      }
      const data = await get<ChatHistoryResponse>(
        `/projects/${projectId}/chat`,
      );
      useChatStore.getState().loadHistory(data.messages);
      return data;
    },
    enabled: !!projectId,
  });
}

export function useSendMessage(projectId: string | undefined) {
  return useMutation({
    mutationFn: async (message: string) => {
      if (isDemoMode(projectId)) {
        const messageId = `demo-sent-${crypto.randomUUID()}`;
        // Simulate PM response via events (same path as real WebSocket)
        simulatePmResponse(message, useAgentStore.getState().addEvent);
        return { message_id: messageId };
      }
      return post<SendMessageResponse>(`/projects/${projectId}/chat`, {
        message,
      });
    },
  });
}
