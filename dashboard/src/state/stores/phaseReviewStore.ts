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

  // Artifact review
  phaseSummaryPath: string;
  chatHistory: ChatMessage[];
  currentChatContent: string;

  // Closing message
  closingMessage: string;
  closingContent: string;

  // Actions
  startWaitingForReview: (phase: string) => void;
  beginReview: (phase: string, opening: string, closing: string, phaseSummaryPath: string) => void;
  startOpeningMessage: (phase: string, opening: string, closing: string, phaseSummaryPath: string) => void;
  setOpeningContent: (content: string) => void;
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
  phaseSummaryPath: "",
  chatHistory: [],
  currentChatContent: "",
  closingMessage: "",
  closingContent: "",

  startWaitingForReview: (phase) =>
    set({
      status: "waiting_to_start",
      currentPhase: phase,
      pmState: "idle",
    }),

  beginReview: (phase, opening, closing, phaseSummaryPath) =>
    set({
      status: "opening_message",
      currentPhase: phase,
      openingMessage: opening,
      openingContent: "",
      closingMessage: closing,
      phaseSummaryPath,
      pmState: "active",
      chatHistory: [],
      currentChatContent: "",
    }),

  startOpeningMessage: (phase, opening, closing, phaseSummaryPath) =>
    set({
      status: "opening_message",
      currentPhase: phase,
      openingMessage: opening,
      openingContent: "",
      closingMessage: closing,
      phaseSummaryPath,
      pmState: "active",
      chatHistory: [],
      currentChatContent: "",
    }),

  setOpeningContent: (content) =>
    set({ openingContent: content }),

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
    set({
      status: "closing_message",
      closingMessage: closing,
      closingContent: "",
      pmState: "active",
    }),

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
      phaseSummaryPath: "",
      chatHistory: [],
      currentChatContent: "",
      closingMessage: "",
      closingContent: "",
    }),

  reset: () =>
    set({
      status: "not_started",
      pmState: "idle",
      currentPhase: null,
      openingMessage: "",
      openingContent: "",
      phaseSummaryPath: "",
      chatHistory: [],
      currentChatContent: "",
      closingMessage: "",
      closingContent: "",
    }),

  setPmState: (pmState) => set({ pmState }),
}));
