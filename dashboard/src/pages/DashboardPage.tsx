import { useState, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PhaseTimeline } from "@/components/PhaseTimeline";
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

  // Build center notification for the swarm circle
  const centerNotification = useMemo(() => {
    if (interrupt) {
      return {
        type: "interrupt" as const,
        message: "I have a question that needs your input.",
        buttonLabel: "Respond in Chat",
        onAction: () => navigate("chat"),
      };
    }
    if (project?.phase_status === "AWAITING_APPROVAL" && project.current_phase) {
      return {
        type: "approval" as const,
        message: `The ${project.current_phase} phase is ready for your review.`,
        buttonLabel: "Review",
        onAction: () => navigate("chat"),
      };
    }
    return null;
  }, [interrupt, project?.phase_status, project?.current_phase, navigate]);

  return (
    <div className="space-y-4">
      {/* Header row */}
      <div className="flex items-center gap-3">
        <h2 className="text-2xl font-bold">Project Overview</h2>
        <Badge variant={wsStatus === "connected" ? "default" : "outline"}>
          {wsStatus === "connected" ? "Live" : "Offline"}
        </Badge>
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
            notification={centerNotification}
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
