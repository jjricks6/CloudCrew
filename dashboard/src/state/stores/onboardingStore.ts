/**
 * Onboarding store — manages PM-led onboarding wizard state.
 *
 * State machine:
 *   not_started → in_progress → sow_review → wrapup → completed
 *                                    ↑ revise ↓
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

  // Actions
  start: () => void;
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

  start: () =>
    set({
      status: "in_progress",
      currentStep: 0,
      pmState: "idle",
      currentQuestionText: "",
      answers: {},
      sowContent: "",
      isRevision: false,
    }),

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
    });
  },
}));
