/**
 * Slide-out panel showing details for a selected agent.
 * Displays name, status, current task, and recent events.
 */

import { useEffect } from "react";
import { motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import type { AgentActivity, SwarmTimelineEvent } from "@/lib/types";
import { formatRelativeTime } from "@/lib/time";
import { getAgentConfig } from "./swarm-constants";

interface AgentDetailPanelProps {
  agent: AgentActivity;
  events: SwarmTimelineEvent[];
  onClose: () => void;
}

export function AgentDetailPanel({
  agent,
  events,
  onClose,
}: AgentDetailPanelProps) {
  const config = getAgentConfig(agent.agent_name);
  const agentEvents = events.filter(
    (e) => e.agentName === agent.agent_name || e.fromAgent === agent.agent_name,
  );

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/20"
        onClick={onClose}
        aria-hidden
      />

      {/* Panel */}
      <motion.div
        role="dialog"
        aria-modal="true"
        aria-label={`${config.label} details`}
        initial={{ x: "100%" }}
        animate={{ x: 0 }}
        exit={{ x: "100%" }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="fixed right-0 top-0 z-50 flex h-full w-80 flex-col border-l bg-card shadow-xl"
      >
        {/* Header */}
        <div className="flex items-center gap-3 border-b p-4">
          <div
            className="flex h-10 w-10 items-center justify-center rounded-full border-2"
            style={{ borderColor: config.color }}
          >
            <span className="text-sm font-bold" style={{ color: config.color }}>
              {config.abbr}
            </span>
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-foreground">{config.label}</h3>
            <Badge
              variant={agent.status === "idle" ? "secondary" : "default"}
              className="mt-0.5 text-[10px]"
            >
              {agent.status}
            </Badge>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close panel"
            className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Current task */}
        <div className="border-b p-4">
          <h4 className="text-xs font-medium text-muted-foreground">
            Current Task
          </h4>
          <p className="mt-1 text-sm text-foreground">
            {agent.detail || "No active task"}
          </p>
        </div>

        {/* Phase */}
        <div className="border-b px-4 py-3">
          <h4 className="text-xs font-medium text-muted-foreground">Phase</h4>
          <p className="mt-0.5 text-sm text-foreground">{agent.phase}</p>
        </div>

        {/* Recent events */}
        <div className="flex-1 overflow-y-auto p-4">
          <h4 className="mb-2 text-xs font-medium text-muted-foreground">
            Recent Activity
          </h4>
          {agentEvents.length === 0 ? (
            <p className="text-xs text-muted-foreground">No events yet.</p>
          ) : (
            <ul className="space-y-2">
              {agentEvents.slice(0, 15).map((ev) => (
                <li key={ev.id} className="text-xs">
                  <span className="text-muted-foreground">
                    {formatRelativeTime(ev.timestamp)}
                  </span>{" "}
                  <span className="text-foreground">{ev.detail}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </motion.div>
    </>
  );
}
