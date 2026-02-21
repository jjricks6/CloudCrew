/**
 * TanStack Query hooks for kanban board tasks.
 *
 * In demo mode, returns mock board tasks without hitting the backend.
 */

import { useQuery } from "@tanstack/react-query";
import { get } from "@/lib/api";
import type { BoardTask } from "@/lib/types";
import { isDemoMode, DEMO_BOARD_TASKS } from "@/lib/demo";

interface BoardTasksResponse {
  project_id: string;
  tasks: BoardTask[];
}

export function useBoardTasks(projectId: string | undefined) {
  return useQuery<BoardTask[]>({
    queryKey: ["board-tasks", projectId],
    queryFn: async () => {
      if (isDemoMode(projectId)) return structuredClone(DEMO_BOARD_TASKS);
      const res = await get<BoardTasksResponse>(
        `/projects/${projectId}/tasks`,
      );
      return res.tasks;
    },
    enabled: !!projectId,
    refetchInterval: isDemoMode(projectId) ? false : 15_000,
  });
}
