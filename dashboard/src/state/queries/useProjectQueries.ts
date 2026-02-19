/**
 * TanStack Query hooks for project data.
 */

import { useQuery } from "@tanstack/react-query";
import { get } from "@/lib/api";
import type { ProjectStatus } from "@/lib/types";

export function useProjectStatus(projectId: string | undefined) {
  return useQuery<ProjectStatus>({
    queryKey: ["project", projectId],
    queryFn: () => get<ProjectStatus>(`/projects/${projectId}/status`),
    enabled: !!projectId,
    refetchInterval: 30_000,
  });
}

export function useProjectDeliverables(projectId: string | undefined) {
  return useQuery<ProjectStatus["deliverables"]>({
    queryKey: ["deliverables", projectId],
    queryFn: () =>
      get<ProjectStatus["deliverables"]>(
        `/projects/${projectId}/deliverables`,
      ),
    enabled: !!projectId,
  });
}
