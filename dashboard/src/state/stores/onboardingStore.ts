/**
 * Onboarding store — manages PM-led onboarding wizard state.
 *
 * State machine:
 *   not_started → in_progress → sow_review → wrapup → completed
 *                                    ↑ revise ↓
 *
 * Supports two modes:
 *   - Demo mode: driven by useDemoEngine with scripted ONBOARDING_STEPS
 *   - Real mode: driven by PM agent interrupts arriving via WebSocket
 *
 * In demo mode, sessionStorage persists the "completed" status so page
 * refreshes skip straight to the full dashboard. Closing the tab resets.
 */

import { create } from "zustand";

type OnboardingStatus = "not_started" | "in_progress" | "sow_review" | "wrapup" | "completed";
type PmVisualState = "active" | "thinking" | "idle";

const STORAGE_KEY = "cloudcrew-onboarding-status";

interface OnboardingState {
  status: OnboardingStatus;
  currentStep: number;
  pmState: PmVisualState;
  currentQuestionText: string;
  answers: Record<number, string>;
  sowContent: string;
  isRevision: boolean;

  /** True when driven by real PM agent interrupts (not demo script). */
  isRealMode: boolean;
  /** Interrupt ID for the current PM question (real mode only). */
  liveInterruptId: string | null;
  /** Dynamic thinking message shown while PM is working (real mode). */
  thinkingMessage: string;
  /** Number of questions answered (real mode — drives thinking text). */
  questionsAnswered: number;

  // Actions
  start: () => void;
  /** Start onboarding in real mode (PM agent, not demo script). */
  startReal: () => void;
  /** Set a dynamic question from a PM interrupt (real mode). */
  setLiveQuestion: (question: string, interruptId: string) => void;
  /** Update the thinking message (e.g. from agent_active events). */
  setThinkingMessage: (message: string) => void;
  setPmState: (state: PmVisualState) => void;
  appendQuestionChunk: (chunk: string) => void;
  setFullQuestion: (text: string) => void;
  answerStep: (answer: string) => void;
  advanceStep: () => void;
  enterSowReview: (sowMarkdown: string) => void;
  requestRevision: () => void;
  enterWrapup: () => void;
  complete: () => void;
  reset: () => void;
}

function loadPersistedStatus(): OnboardingStatus {
  try {
    const stored = sessionStorage.getItem(STORAGE_KEY);
    if (stored === "completed") return "completed";
  } catch {
    // sessionStorage unavailable (SSR, privacy mode) — start fresh
  }
  return "not_started";
}

function persistStatus(status: OnboardingStatus): void {
  try {
    if (status === "completed") {
      sessionStorage.setItem(STORAGE_KEY, "completed");
    } else {
      sessionStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    // Ignore storage errors
  }
}

export const useOnboardingStore = create<OnboardingState>()((set) => ({
  status: loadPersistedStatus(),
  currentStep: 0,
  pmState: "idle",
  currentQuestionText: "",
  answers: {},
  sowContent: "",
  isRevision: false,
  isRealMode: false,
  liveInterruptId: null,
  thinkingMessage: "",
  questionsAnswered: 0,

  start: () =>
    set({
      status: "in_progress",
      currentStep: 0,
      pmState: "idle",
      currentQuestionText: "",
      answers: {},
      sowContent: "",
      isRevision: false,
      isRealMode: false,
      liveInterruptId: null,
      thinkingMessage: "",
      questionsAnswered: 0,
    }),

  startReal: () =>
    set({
      status: "in_progress",
      isRealMode: true,
      currentStep: 0,
      pmState: "thinking",
      currentQuestionText: "",
      answers: {},
      sowContent: "",
      isRevision: false,
      liveInterruptId: null,
      thinkingMessage: "Analyzing your project details and preparing questions",
      questionsAnswered: 0,
    }),

  setLiveQuestion: (question, interruptId) =>
    set({
      currentQuestionText: question,
      liveInterruptId: interruptId,
      pmState: "idle",
    }),

  setThinkingMessage: (message) => set({ thinkingMessage: message }),

  setPmState: (pmState) => set({ pmState }),

  appendQuestionChunk: (chunk) =>
    set((s) => ({ currentQuestionText: s.currentQuestionText + chunk })),

  setFullQuestion: (text) => set({ currentQuestionText: text }),

  answerStep: (answer) =>
    set((s) => ({
      answers: { ...s.answers, [s.currentStep]: answer },
    })),

  advanceStep: () =>
    set((s) => ({
      currentStep: s.currentStep + 1,
      currentQuestionText: "",
    })),

  enterSowReview: (sowMarkdown) =>
    set({
      status: "sow_review",
      pmState: "thinking",
      sowContent: sowMarkdown,
      isRevision: false,
    }),

  requestRevision: () =>
    set({
      status: "in_progress",
      currentQuestionText: "",
      isRevision: true,
    }),

  enterWrapup: () =>
    set({
      status: "wrapup",
      currentQuestionText: "",
    }),

  complete: () => {
    persistStatus("completed");
    set({
      status: "completed",
      pmState: "idle",
    });
  },

  reset: () => {
    persistStatus("not_started");
    set({
      status: "not_started",
      currentStep: 0,
      pmState: "idle",
      currentQuestionText: "",
      answers: {},
      sowContent: "",
      isRevision: false,
      isRealMode: false,
      liveInterruptId: null,
      thinkingMessage: "",
      questionsAnswered: 0,
    });
  },
}));
