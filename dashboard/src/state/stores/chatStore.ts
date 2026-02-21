/**
 * Zustand store for PM chat state with streaming support.
 *
 * Handles message history, real-time token streaming from WebSocket,
 * and thinking indicators.
 */

import { create } from "zustand";
import type { ChatMessage } from "@/lib/types";

interface ChatState {
  messages: ChatMessage[];
  isThinking: boolean;
  streamingContent: string;

  addMessage: (msg: ChatMessage) => void;
  appendChunk: (content: string) => void;
  finalizeStream: (messageId: string) => void;
  setThinking: (v: boolean) => void;
  loadHistory: (msgs: ChatMessage[]) => void;
  reset: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isThinking: false,
  streamingContent: "",

  addMessage: (msg) =>
    set((state) => ({
      messages: [...state.messages, msg],
    })),

  appendChunk: (content) =>
    set((state) => ({
      streamingContent: state.streamingContent + content,
      isThinking: false,
    })),

  finalizeStream: (messageId) =>
    set((state) => {
      if (!state.streamingContent) return state;
      const finalMessage: ChatMessage = {
        message_id: messageId,
        role: "pm",
        content: state.streamingContent,
        timestamp: new Date().toISOString(),
      };
      return {
        messages: [...state.messages, finalMessage],
        streamingContent: "",
        isThinking: false,
      };
    }),

  setThinking: (v) =>
    set({
      isThinking: v,
      streamingContent: "",
    }),

  loadHistory: (msgs) =>
    set((state) => {
      // Merge server history with any optimistic messages already in the store,
      // deduplicating by message_id so we don't lose in-flight messages.
      const historyIds = new Set(msgs.map((m) => m.message_id));
      const optimistic = state.messages.filter(
        (m) => !historyIds.has(m.message_id),
      );
      return { messages: [...msgs, ...optimistic] };
    }),

  reset: () =>
    set({
      messages: [],
      isThinking: false,
      streamingContent: "",
    }),
}));
