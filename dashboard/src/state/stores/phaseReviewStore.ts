/**
 * Phase review store — manages step-by-step PM-led phase review.
 *
 * State machine:
 *   not_started → waiting_to_start → reviewing → final_review → completed
 *
 * When a phase reaches AWAITING_APPROVAL status, the user sees a "Review" button
 * in the dashboard. Clicking it enters reviewing mode. The PM presents review content
 * one step at a time, allowing user comments at each step. After all steps are
 * complete, the final review screen shows all content for approval/revision.
 */

import { create } from "zustand";

export type PhaseReviewStatus =
  | "not_started"
  | "waiting_to_start"
  | "reviewing"
  | "final_review"
  | "transitioning"
  | "completed";

export type PmVisualState = "active" | "thinking" | "idle";

export interface ReviewStep {
  id: string;
  type: "summary" | "decisions" | "artifacts";
  title: string;
  content: string;
  userComment?: string;
}

interface PhaseReviewState {
  status: PhaseReviewStatus;
  pmState: PmVisualState;
  currentPhase: string | null;
  currentStepIndex: number;
  steps: ReviewStep[];
  currentStepContent: string;

  // Actions
  startWaitingForReview: (phase: string) => void;
  beginReview: (phase: string, steps: ReviewStep[]) => void;
  setPmState: (state: PmVisualState) => void;
  appendStepChunk: (chunk: string) => void;
  setFullStepContent: (text: string) => void;
  addUserComment: (comment: string) => void;
  advanceToNextStep: () => void;
  moveToFinalReview: () => void;
  startTransition: () => void;
  completeReview: () => void;
  reset: () => void;
}

export const usePhaseReviewStore = create<PhaseReviewState>()((set) => ({
  status: "not_started",
  pmState: "idle",
  currentPhase: null,
  currentStepIndex: 0,
  steps: [],
  currentStepContent: "",

  startWaitingForReview: (phase) =>
    set({
      status: "waiting_to_start",
      currentPhase: phase,
      pmState: "idle",
    }),

  beginReview: (phase, steps) =>
    set({
      status: "reviewing",
      currentPhase: phase,
      steps,
      currentStepIndex: 0,
      pmState: "active",
      currentStepContent: "",
    }),

  setPmState: (pmState) => set({ pmState }),

  appendStepChunk: (chunk) =>
    set((s) => ({ currentStepContent: s.currentStepContent + chunk })),

  setFullStepContent: (text) => set({ currentStepContent: text }),

  addUserComment: (comment) =>
    set((s) => {
      const updatedSteps = [...s.steps];
      if (updatedSteps[s.currentStepIndex]) {
        updatedSteps[s.currentStepIndex].userComment = comment;
      }
      return { steps: updatedSteps };
    }),

  advanceToNextStep: () =>
    set((s) => {
      const nextIndex = s.currentStepIndex + 1;
      if (nextIndex >= s.steps.length) {
        // All steps completed, move to final review
        return {
          currentStepIndex: nextIndex,
          status: "final_review" as const,
          pmState: "thinking",
          currentStepContent: "",
        };
      }
      return {
        currentStepIndex: nextIndex,
        pmState: "active",
        currentStepContent: "",
      };
    }),

  moveToFinalReview: () =>
    set({
      status: "final_review",
      pmState: "idle",
      currentStepContent: "",
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
      currentStepIndex: 0,
      steps: [],
      currentStepContent: "",
    }),

  reset: () =>
    set({
      status: "not_started",
      pmState: "idle",
      currentPhase: null,
      currentStepIndex: 0,
      steps: [],
      currentStepContent: "",
    }),
}));
