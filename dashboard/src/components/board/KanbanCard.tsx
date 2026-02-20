/**
 * A single task card in a kanban column.
 *
 * Displays title, phase badge, assigned agent, and comment count.
 * Click to open the detail panel.
 */

import { Badge } from "@/components/ui/badge";
import type { BoardTask } from "@/lib/types";

const AGENT_COLORS: Record<string, string> = {
  pm: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  sa: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
  dev: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  infra: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
  data: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200",
  security: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  qa: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
};

interface KanbanCardProps {
  task: BoardTask;
  onClick: () => void;
}

export function KanbanCard({ task, onClick }: KanbanCardProps) {
  const agentColor =
    AGENT_COLORS[task.assigned_to] ??
    "bg-muted text-muted-foreground";

  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full rounded-lg border bg-card p-3 text-left shadow-sm transition-colors hover:bg-accent/50"
    >
      <p className="text-sm font-medium leading-snug">{task.title}</p>

      <div className="mt-2 flex items-center gap-2">
        <Badge variant="outline" className="text-[10px]">
          {task.phase}
        </Badge>
        <span
          className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${agentColor}`}
        >
          {task.assigned_to}
        </span>
      </div>

      {task.comments.length > 0 && (
        <div className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
          <svg className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
            <path
              fillRule="evenodd"
              d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z"
              clipRule="evenodd"
            />
          </svg>
          <span>{task.comments.length}</span>
        </div>
      )}
    </button>
  );
}
