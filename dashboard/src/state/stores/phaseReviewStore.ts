/**
 * Phase review store — manages PM-led artifact review with chat.
 *
 * State machine:
 *   not_started → waiting_to_start → opening_message → artifact_review → closing_message → transitioning → completed
 *
 * Flow:
 * 1. User clicks Review button when phase reaches AWAITING_APPROVAL status
 * 2. PM shows opening message welcoming to review (user clicks Continue)
 * 3. Artifact review screen shows all artifacts with chat interface
 * 4. User can review documents, ask questions, and eventually approve
 * 5. PM shows closing thank-you message
 * 6. Transition to next phase begins
 */

import { create } from "zustand";

export type PhaseReviewStatus =
  | "not_started"
  | "waiting_to_start"
  | "opening_message"
  | "artifact_review"
  | "closing_message"
  | "closing_complete"
  | "transitioning"
  | "completed";

export type PmVisualState = "active" | "thinking" | "idle";

export interface ChatMessage {
  id: string;
  role: "user" | "pm";
  content: string;
  timestamp: number;
}

interface PhaseReviewState {
  status: PhaseReviewStatus;
  pmState: PmVisualState;
  currentPhase: string | null;

  // Opening message
  openingMessage: string;
  openingContent: string;
  openingMessageComplete: boolean;

  // Artifact review
  phaseSummaryPath: string;
  chatHistory: ChatMessage[];
  currentChatContent: string;

  // Closing message
  closingMessage: string;
  closingContent: string;
  closingMessageComplete: boolean;

  // Actions
  startWaitingForReview: (phase: string) => void;
  beginReview: (phase: string, opening: string, closing: string, phaseSummaryPath: string) => void;
  startOpeningMessage: (phase: string, opening: string, closing: string, phaseSummaryPath: string) => void;
  setOpeningContent: (content: string) => void;
  appendMessageContent: (messageType: "opening" | "closing", chunk: string) => void;
  setMessageComplete: (messageType: "opening" | "closing") => void;
  advanceToArtifactReview: () => void;
  addUserChatMessage: (content: string) => void;
  appendChatChunk: (chunk: string) => void;
  completeChatMessage: () => void;
  advanceToClosingMessage: (closing: string) => void;
  setClosingContent: (content: string) => void;
  advanceFromClosing: () => void;
  startTransition: () => void;
  completeReview: () => void;
  reset: () => void;
  setPmState: (state: PmVisualState) => void;
}

export const usePhaseReviewStore = create<PhaseReviewState>()((set) => ({
  status: "not_started",
  pmState: "idle",
  currentPhase: null,
  openingMessage: "",
  openingContent: "",
  openingMessageComplete: false,
  phaseSummaryPath: "",
  chatHistory: [],
  currentChatContent: "",
  closingMessage: "",
  closingContent: "",
  closingMessageComplete: false,

  startWaitingForReview: (phase) =>
    set({
      status: "waiting_to_start",
      currentPhase: phase,
      pmState: "idle",
    }),

  beginReview: (phase, opening, closing, phaseSummaryPath) =>
    set((s) => {
      // If there's no opening message (e.g., Discovery phase), skip directly
      // to artifact review — no PM welcome screen needed.
      const hasStreamedOpening = s.openingContent.length > 0;
      const hasOpening = hasStreamedOpening || !!opening;
      if (!hasOpening) {
        return {
          status: "artifact_review",
          currentPhase: phase,
          openingMessage: "",
          openingContent: "",
          openingMessageComplete: true,
          closingMessage: closing,
          phaseSummaryPath,
          pmState: "thinking",
          chatHistory: [],
          currentChatContent: "",
        };
      }

      // Use persisted message from API if no WebSocket content has arrived.
      // This handles the case where the user opens review after the PM Lambda
      // already finished (WebSocket stream was missed or user wasn't connected).
      const effectiveOpeningContent = hasStreamedOpening ? s.openingContent : opening;
      const isOpeningComplete = s.openingMessageComplete || (!hasStreamedOpening && !!opening);
      return {
        status: "opening_message",
        currentPhase: phase,
        openingMessage: opening,
        openingContent: effectiveOpeningContent,
        openingMessageComplete: isOpeningComplete,
        closingMessage: closing,
        phaseSummaryPath,
        pmState: isOpeningComplete ? "thinking" : "active",
        chatHistory: [],
        currentChatContent: "",
      };
    }),

  startOpeningMessage: (phase, opening, closing, phaseSummaryPath) =>
    set((s) => ({
      status: "opening_message",
      currentPhase: phase,
      openingMessage: opening,
      openingContent: s.openingContent,
      closingMessage: closing,
      phaseSummaryPath,
      pmState: s.openingMessageComplete ? "thinking" : "active",
      chatHistory: [],
      currentChatContent: "",
    })),

  setOpeningContent: (content) =>
    set({ openingContent: content }),

  appendMessageContent: (messageType, chunk) =>
    set((s) => {
      if (messageType === "opening") {
        return { openingContent: s.openingContent + chunk };
      } else {
        return { closingContent: s.closingContent + chunk };
      }
    }),

  setMessageComplete: (messageType) =>
    set((s) => {
      if (messageType === "opening") {
        return {
          openingMessageComplete: true,
          // If we're already showing the opening message, update PM state
          pmState: s.status === "opening_message" ? "thinking" : s.pmState,
        };
      } else {
        return {
          closingMessageComplete: true,
          pmState: s.status === "closing_message" ? "thinking" : s.pmState,
        };
      }
    }),

  advanceToArtifactReview: () =>
    set({
      status: "artifact_review",
      pmState: "thinking",
      openingContent: "",
    }),

  addUserChatMessage: (content) =>
    set((s) => ({
      chatHistory: [
        ...s.chatHistory,
        {
          id: crypto.randomUUID(),
          role: "user",
          content,
          timestamp: Date.now(),
        },
      ],
      currentChatContent: "",
      pmState: "active",
    })),

  appendChatChunk: (chunk) =>
    set((s) => ({ currentChatContent: s.currentChatContent + chunk })),

  completeChatMessage: () =>
    set((s) => ({
      chatHistory: [
        ...s.chatHistory,
        {
          id: crypto.randomUUID(),
          role: "pm",
          content: s.currentChatContent,
          timestamp: Date.now(),
        },
      ],
      currentChatContent: "",
      pmState: "thinking",
    })),

  advanceToClosingMessage: (closing) =>
    set((s) => ({
      status: "closing_message",
      closingMessage: closing,
      // Preserve any closing content already streamed
      closingContent: s.closingContent,
      pmState: s.closingMessageComplete ? "thinking" : "active",
    })),

  setClosingContent: (content) =>
    set({ closingContent: content }),

  advanceFromClosing: () =>
    set({
      status: "closing_complete",
      pmState: "idle",
    }),

  startTransition: () =>
    set({
      status: "transitioning",
      pmState: "active",
    }),

  completeReview: () =>
    set({
      status: "completed",
      pmState: "idle",
      currentPhase: null,
      openingMessage: "",
      openingContent: "",
      openingMessageComplete: false,
      phaseSummaryPath: "",
      chatHistory: [],
      currentChatContent: "",
      closingMessage: "",
      closingContent: "",
      closingMessageComplete: false,
    }),

  reset: () =>
    set({
      status: "not_started",
      pmState: "idle",
      currentPhase: null,
      openingMessage: "",
      openingContent: "",
      openingMessageComplete: false,
      phaseSummaryPath: "",
      chatHistory: [],
      currentChatContent: "",
      closingMessage: "",
      closingContent: "",
      closingMessageComplete: false,
    }),

  setPmState: (pmState) => set({ pmState }),
}));
