import { useState } from "react";
import { useParams } from "react-router-dom";
import { Skeleton } from "@/components/ui/skeleton";
import { KanbanColumn } from "@/components/board/KanbanColumn";
import { TaskDetailPanel } from "@/components/board/TaskDetailPanel";
import { useBoardTasks } from "@/state/queries/useBoardQueries";
import { KANBAN_COLUMNS, type BoardTask } from "@/lib/types";

export function BoardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: tasks, isLoading } = useBoardTasks(projectId);
  const [selectedTask, setSelectedTask] = useState<BoardTask | null>(null);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold">Task Board</h2>
        <div className="grid gap-4 md:grid-cols-4">
          {KANBAN_COLUMNS.map((col) => (
            <Skeleton key={col} className="h-[400px] rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  const grouped = KANBAN_COLUMNS.reduce(
    (acc, col) => {
      acc[col] = (tasks ?? []).filter((t) => t.status === col);
      return acc;
    },
    {} as Record<string, BoardTask[]>,
  );

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Task Board</h2>

      <div className="grid gap-4 md:grid-cols-4">
        {KANBAN_COLUMNS.map((col) => (
          <KanbanColumn
            key={col}
            column={col}
            tasks={grouped[col]}
            onTaskClick={setSelectedTask}
          />
        ))}
      </div>

      {selectedTask && (
        <TaskDetailPanel
          task={selectedTask}
          onClose={() => setSelectedTask(null)}
        />
      )}
    </div>
  );
}
