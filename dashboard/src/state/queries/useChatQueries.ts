/**
 * TanStack Query hooks for PM chat.
 */

import { useMutation, useQuery } from "@tanstack/react-query";
import { get, post } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";
import { useChatStore } from "@/state/stores/chatStore";

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
      return post<SendMessageResponse>(`/projects/${projectId}/chat`, {
        message,
      });
    },
  });
}
