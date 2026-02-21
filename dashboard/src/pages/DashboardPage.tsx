import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PhaseTimeline } from "@/components/PhaseTimeline";
import { ApprovalBanner } from "@/components/approval/ApprovalBanner";
import { SwarmVisualization } from "@/components/swarm/SwarmVisualization";
import { ActivityTimeline } from "@/components/swarm/ActivityTimeline";
import { AgentDetailPanel } from "@/components/swarm/AgentDetailPanel";
import { useAgentStore } from "@/state/stores/agentStore";
import { useProjectStatus } from "@/state/queries/useProjectQueries";
import type { AgentActivity } from "@/lib/types";

export function DashboardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const wsStatus = useAgentStore((s) => s.wsStatus);
  const agents = useAgentStore((s) => s.agents);
  const interrupt = useAgentStore((s) => s.pendingInterrupt);
  const swarmEvents = useAgentStore((s) => s.swarmEvents);
  const activeHandoff = useAgentStore((s) => s.activeHandoff);
  const [selectedAgent, setSelectedAgent] = useState<AgentActivity | null>(null);

  const { data: project, isLoading: projectLoading } =
    useProjectStatus(projectId);

  return (
    <div className="space-y-4">
      {/* Header row */}
      <div className="flex items-center gap-3">
        <h2 className="text-2xl font-bold">Project Overview</h2>
        <Badge variant={wsStatus === "connected" ? "default" : "outline"}>
          {wsStatus === "connected" ? "Live" : "Offline"}
        </Badge>
      </div>

      {/* Notifications */}
      {interrupt && (
        <div className="flex items-center justify-between rounded-lg border border-yellow-500/30 bg-yellow-50 px-4 py-3 dark:bg-yellow-950/20">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-yellow-800 dark:text-yellow-300">
              The agent has a question about the {interrupt.phase} phase.
            </span>
            <Badge variant="secondary" className="text-xs">
              Input Needed
            </Badge>
          </div>
          <Button size="sm" onClick={() => navigate("chat")}>
            Respond in Chat
          </Button>
        </div>
      )}

      <div>
        <ApprovalBanner
          currentPhase={project?.current_phase}
          phaseStatus={project?.phase_status}
        />
      </div>

      {/* Phase Progress */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Phase Progress</CardTitle>
        </CardHeader>
        <CardContent>
          {projectLoading ? (
            <Skeleton className="h-12 w-full" />
          ) : (
            <PhaseTimeline
              currentPhase={project?.current_phase}
              phaseStatus={project?.phase_status}
            />
          )}
        </CardContent>
      </Card>

      {/* Swarm (center) + Activity (right) — no boxes */}
      <div className="flex h-[calc(100vh-21rem)] min-h-[300px] gap-6">
        {/* Swarm visualization */}
        <div className="relative h-full flex-1">
          <SwarmVisualization
            agents={agents}
            phase={project?.current_phase}
            activeHandoff={activeHandoff}
            onAgentClick={setSelectedAgent}
          />
        </div>

        {/* Activity feed */}
        <div className="flex w-72 shrink-0 flex-col overflow-hidden">
          <h3 className="mb-2 text-sm font-medium text-muted-foreground">
            Activity
          </h3>
          <div className="flex-1 overflow-y-auto">
            <ActivityTimeline events={swarmEvents} />
          </div>
        </div>
      </div>

      {/* Agent detail panel (slide-out on click) */}
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
