/**
 * A single kanban column (Backlog, In Progress, Review, Done).
 *
 * Displays a header with count, scrollable card list, and empty state.
 */

import type { BoardTask, KanbanColumn as KanbanColumnType } from "@/lib/types";
import { KanbanCard } from "./KanbanCard";

const COLUMN_LABELS: Record<KanbanColumnType, string> = {
  backlog: "Backlog",
  in_progress: "In Progress",
  review: "Review",
  done: "Done",
};

const COLUMN_DOT_COLORS: Record<KanbanColumnType, string> = {
  backlog: "bg-muted-foreground",
  in_progress: "bg-blue-500",
  review: "bg-yellow-500",
  done: "bg-green-500",
};

interface KanbanColumnProps {
  column: KanbanColumnType;
  tasks: BoardTask[];
  onTaskClick: (task: BoardTask) => void;
}

export function KanbanColumn({
  column,
  tasks,
  onTaskClick,
}: KanbanColumnProps) {
  return (
    <div className="flex min-h-[400px] flex-col rounded-lg border bg-muted/30">
      {/* Column header */}
      <div className="flex items-center gap-2 border-b px-3 py-2.5">
        <span
          className={`h-2 w-2 rounded-full ${COLUMN_DOT_COLORS[column]}`}
        />
        <span className="text-sm font-medium">{COLUMN_LABELS[column]}</span>
        <span className="ml-auto rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
          {tasks.length}
        </span>
      </div>

      {/* Card list */}
      <div className="flex-1 space-y-2 overflow-y-auto p-2">
        {tasks.length > 0 ? (
          tasks.map((task) => (
            <KanbanCard
              key={task.task_id}
              task={task}
              onClick={() => onTaskClick(task)}
            />
          ))
        ) : (
          <p className="p-3 text-center text-xs text-muted-foreground">
            No tasks
          </p>
        )}
      </div>
    </div>
  );
}
