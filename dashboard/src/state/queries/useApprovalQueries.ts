/**
 * TanStack Query mutation hooks for approval gates and interrupt responses.
 *
 * In demo mode, mutates local state instead of calling the backend API.
 */

import { useMutation } from "@tanstack/react-query";
import { post } from "@/lib/api";
import { queryClient } from "@/state/queryClient";
import { useAgentStore } from "@/state/stores/agentStore";
import {
  isDemoMode,
  advanceDemoPhase,
  simulatePmResponse,
} from "@/lib/demo";

interface ApprovalResponse {
  project_id: string;
  phase: string;
  decision: string;
}

interface InterruptResponse {
  project_id: string;
  interrupt_id: string;
  status: string;
}

export function useApprovePhase(projectId: string | undefined) {
  return useMutation({
    mutationFn: async () => {
      if (isDemoMode(projectId)) {
        advanceDemoPhase();
        return { project_id: "demo", phase: "", decision: "APPROVED" };
      }
      return post<ApprovalResponse>(`/projects/${projectId}/approve`, {});
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["project"] });
      void queryClient.invalidateQueries({ queryKey: ["deliverables"] });
    },
  });
}

export function useRevisePhase(projectId: string | undefined) {
  return useMutation({
    mutationFn: async (feedback: string) => {
      if (isDemoMode(projectId)) {
        // In demo, revision keeps current phase — just reset to IN_PROGRESS
        return { project_id: "demo", phase: "", decision: "REVISION_REQUESTED" };
      }
      return post<ApprovalResponse>(`/projects/${projectId}/revise`, {
        feedback,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["project"] });
    },
  });
}

export function useRespondToInterrupt(projectId: string | undefined) {
  return useMutation({
    mutationFn: async ({
      interruptId,
      response,
    }: {
      interruptId: string;
      response: string;
    }) => {
      if (isDemoMode(projectId)) {
        // dismissInterrupt handles clearing demo state + invalidating queries
        useAgentStore.getState().dismissInterrupt();
        // Simulate a PM acknowledgment in chat via events
        simulatePmResponse(
          `[Interrupt response]: ${response}`,
          useAgentStore.getState().addEvent,
        );
        return {
          project_id: "demo",
          interrupt_id: interruptId,
          status: "ANSWERED",
        };
      }
      return post<InterruptResponse>(
        `/projects/${projectId}/interrupt/${interruptId}/respond`,
        { response },
      );
    },
    onSuccess: () => {
      useAgentStore.getState().dismissInterrupt();
      void queryClient.invalidateQueries({ queryKey: ["project"] });
    },
  });
}
