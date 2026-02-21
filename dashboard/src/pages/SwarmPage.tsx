/**
 * Swarm Visualization page — animated real-time view of agents collaborating.
 *
 * Top section: radial agent layout with handoff arcs and thought bubbles.
 * Bottom section: scrollable activity timeline.
 */

import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAgentStore } from "@/state/stores/agentStore";
import { useProjectStatus } from "@/state/queries/useProjectQueries";
import { useProjectId } from "@/lib/useProjectId";
import type { AgentActivity } from "@/lib/types";
import { SwarmVisualization } from "@/components/swarm/SwarmVisualization";
import { ActivityTimeline } from "@/components/swarm/ActivityTimeline";
import { AgentDetailPanel } from "@/components/swarm/AgentDetailPanel";

export function SwarmPage() {
  const projectId = useProjectId();
  const agents = useAgentStore((s) => s.agents);
  const swarmEvents = useAgentStore((s) => s.swarmEvents);
  const activeHandoff = useAgentStore((s) => s.activeHandoff);
  const { data: project, isLoading, isError, error } = useProjectStatus(projectId);
  const [selectedAgent, setSelectedAgent] = useState<AgentActivity | null>(
    null,
  );

  if (isLoading) {
    return (
      <div className="flex h-[calc(100vh-140px)] flex-col gap-4">
        <Skeleton className="flex-[2] rounded-lg" />
        <Skeleton className="min-h-[140px] flex-1 rounded-lg" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="space-y-4">
        <h2 className="text-2xl font-bold">Swarm Visualization</h2>
        <p className="text-sm text-destructive">
          Failed to load project status: {error instanceof Error ? error.message : "Unknown error"}
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-140px)] flex-col gap-4">
      {/* Visualization area */}
      <Card className="flex-[2] overflow-hidden">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">
            Agent Swarm — Live View
          </CardTitle>
        </CardHeader>
        <CardContent className="relative h-[calc(100%-48px)] p-2">
          <SwarmVisualization
            agents={agents}
            phase={project?.current_phase}
            phaseStatus={project?.phase_status}
            activeHandoff={activeHandoff}
            onAgentClick={setSelectedAgent}
          />
        </CardContent>
      </Card>

      {/* Activity timeline */}
      <Card className="min-h-[140px] flex-1">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">
            Activity Feed
          </CardTitle>
        </CardHeader>
        <CardContent className="h-[calc(100%-48px)] overflow-hidden">
          <ActivityTimeline events={swarmEvents} />
        </CardContent>
      </Card>

      {/* Agent detail panel (slide-out) */}
      <AnimatePresence>
        {selectedAgent && (
          <AgentDetailPanel
            key={selectedAgent.agent_name}
            agent={selectedAgent}
            events={swarmEvents}
            onClose={() => setSelectedAgent(null)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
