/**
 * Slide-out detail panel for a board task.
 *
 * Shows title, description, status, assigned agent, comments timeline,
 * and optional artifact link. Dismisses on backdrop click or Escape key.
 */

import { useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import type { BoardTask } from "@/lib/types";

interface TaskDetailPanelProps {
  task: BoardTask;
  onClose: () => void;
}

export function TaskDetailPanel({ task, onClose }: TaskDetailPanelProps) {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/30"
        onClick={onClose}
        onKeyDown={(e) => { if (e.key === "Escape") onClose(); }}
        role="button"
        tabIndex={-1}
        aria-label="Close panel"
      />
    <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l bg-background shadow-lg">
      {/* Header */}
      <div className="flex items-start justify-between border-b p-4">
        <div className="flex-1 pr-4">
          <h3 className="text-lg font-semibold">{task.title}</h3>
          <div className="mt-1 flex items-center gap-2">
            <Badge variant="outline" className="text-xs">
              {task.phase}
            </Badge>
            <Badge
              variant={task.status === "done" ? "default" : "secondary"}
              className="text-xs"
            >
              {task.status.replace("_", " ")}
            </Badge>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-foreground"
        >
          <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path
              fillRule="evenodd"
              d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      </div>

      {/* Body — scrollable */}
      <div className="flex-1 overflow-y-auto p-4">
        {/* Description */}
        <section className="mb-6">
          <h4 className="mb-1 text-xs font-medium uppercase text-muted-foreground">
            Description
          </h4>
          <p className="text-sm leading-relaxed">{task.description}</p>
        </section>

        {/* Details */}
        <section className="mb-6 grid grid-cols-2 gap-3 text-sm">
          <div>
            <span className="text-xs font-medium uppercase text-muted-foreground">
              Assigned To
            </span>
            <p className="mt-0.5 font-medium">{task.assigned_to}</p>
          </div>
          <div>
            <span className="text-xs font-medium uppercase text-muted-foreground">
              Status
            </span>
            <p className="mt-0.5 font-medium">
              {task.status.replace("_", " ")}
            </p>
          </div>
          {task.artifact_path && (
            <div className="col-span-2">
              <span className="text-xs font-medium uppercase text-muted-foreground">
                Artifact
              </span>
              <p className="mt-0.5 font-mono text-xs text-blue-600 dark:text-blue-400">
                {task.artifact_path}
              </p>
            </div>
          )}
        </section>

        {/* Comments */}
        <section>
          <h4 className="mb-3 text-xs font-medium uppercase text-muted-foreground">
            Comments ({task.comments.length})
          </h4>
          {task.comments.length > 0 ? (
            <div className="space-y-3">
              {task.comments.map((c, i) => (
                <div
                  key={`${c.timestamp}-${i}`}
                  className="rounded-md border bg-muted/40 p-3"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium">{c.author}</span>
                    <span className="text-muted-foreground">
                      {new Date(c.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <p className="mt-1 text-sm">{c.content}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No comments yet.</p>
          )}
        </section>
      </div>
    </div>
    </>
  );
}
