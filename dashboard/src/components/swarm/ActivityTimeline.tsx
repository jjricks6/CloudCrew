/**
 * Scrollable feed of recent agent activity.
 * Each entry shows the agent name and what they're working on.
 * New entries animate in from the top.
 */

import { motion, AnimatePresence } from "framer-motion";
import type { SwarmTimelineEvent } from "@/lib/types";
import { formatRelativeTime } from "@/lib/time";
import { getAgentConfig } from "./swarm-constants";

interface ActivityTimelineProps {
  events: SwarmTimelineEvent[];
}

export function ActivityTimeline({ events }: ActivityTimelineProps) {
  if (events.length === 0) {
    return (
      <p className="py-4 text-center text-sm text-muted-foreground">
        No activity yet. Events will appear here as agents work.
      </p>
    );
  }

  return (
    <div className="overflow-y-auto pr-1">
      <AnimatePresence initial={false}>
        {events.map((ev) => {
          const config = getAgentConfig(ev.agentName);
          return (
            <motion.div
              key={ev.id}
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3, ease: "easeOut" }}
              className="overflow-hidden"
            >
              <div className="flex items-start gap-2 border-b border-border/50 py-2 text-xs">
                <span
                  className="mt-1 h-2 w-2 shrink-0 rounded-full"
                  style={{ backgroundColor: config.color }}
                />
                <div className="min-w-0 flex-1">
                  <span className="font-medium" style={{ color: config.color }}>
                    {config.label}
                  </span>{" "}
                  <span className="text-muted-foreground line-clamp-1">
                    {ev.detail}
                  </span>
                </div>
                <span className="shrink-0 text-muted-foreground">
                  {formatRelativeTime(ev.timestamp)}
                </span>
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
