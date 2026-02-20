/**
 * TanStack Query hooks for project data.
 *
 * In demo mode, returns mock project status without hitting the backend.
 */

import { useQuery } from "@tanstack/react-query";
import { get } from "@/lib/api";
import type { ProjectStatus, ProjectStatusSummary } from "@/lib/types";
import { isDemoMode, DEMO_PROJECT_STATUS } from "@/lib/demo";

/** GET /projects/{id}/status — returns slim summary (not full ledger). */
export function useProjectStatus(projectId: string | undefined) {
  return useQuery<ProjectStatusSummary>({
    queryKey: ["project", projectId],
    queryFn: () => {
      if (isDemoMode(projectId)) return DEMO_PROJECT_STATUS;
      return get<ProjectStatusSummary>(`/projects/${projectId}/status`);
    },
    enabled: !!projectId,
    refetchInterval: isDemoMode(projectId) ? false : 30_000,
  });
}

export function useProjectDeliverables(projectId: string | undefined) {
  return useQuery<ProjectStatus["deliverables"]>({
    queryKey: ["deliverables", projectId],
    queryFn: () => {
      if (isDemoMode(projectId)) return DEMO_PROJECT_STATUS.deliverables;
      return get<ProjectStatus["deliverables"]>(
        `/projects/${projectId}/deliverables`,
      );
    },
    enabled: !!projectId,
  });
}
