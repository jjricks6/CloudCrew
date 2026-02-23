import { useState, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { PhaseTimeline } from "@/components/PhaseTimeline";
import { SwarmVisualization } from "@/components/swarm/SwarmVisualization";
import { ActivityTimeline } from "@/components/swarm/ActivityTimeline";
import { AgentDetailPanel } from "@/components/swarm/AgentDetailPanel";
import { OnboardingView } from "@/components/onboarding/OnboardingView";
import { PhaseReviewView } from "@/components/phase-review/PhaseReviewView";
import { useAgentStore } from "@/state/stores/agentStore";
import { useOnboardingStore } from "@/state/stores/onboardingStore";
import { usePhaseReviewStore } from "@/state/stores/phaseReviewStore";
import { useProjectStatus } from "@/state/queries/useProjectQueries";
import { PHASE_PLAYBOOKS } from "@/lib/demoTimeline";
import type { AgentActivity } from "@/lib/types";

export function DashboardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const onboardingStatus = useOnboardingStore((s) => s.status);
  const phaseReviewStatus = usePhaseReviewStore((s) => s.status);
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
    if (
      project?.phase_status === "AWAITING_APPROVAL" &&
      project.current_phase &&
      phaseReviewStatus === "not_started"
    ) {
      return {
        type: "approval" as const,
        message: `The ${project.current_phase} phase is ready for your review.`,
        buttonLabel: "Review",
        onAction: () => {
          usePhaseReviewStore
            .getState()
            .startWaitingForReview(project.current_phase);
        },
      };
    }
    return null;
  }, [interrupt, project, phaseReviewStatus, navigate]);

  // Show onboarding wizard until completed
  if (onboardingStatus !== "completed") {
    return <OnboardingView />;
  }

  // Show phase review wizard when user clicks Review button
  if (phaseReviewStatus !== "not_started" && phaseReviewStatus !== "completed") {
    return <PhaseReviewView />;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="space-y-4"
    >
      {/* Header row */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h2 className="text-2xl font-bold">
            {project?.project_name ?? "Project"} Dashboard
          </h2>
          <Badge variant={wsStatus === "connected" ? "default" : "outline"}>
            {wsStatus === "connected" ? "Live" : "Offline"}
          </Badge>
        </div>
        {/* DEBUG: Skip to review button */}
        {project?.phase_status === "IN_PROGRESS" && (
          <Button
            onClick={() => {
              const phase = project.current_phase;
              const playbook = PHASE_PLAYBOOKS.find((p) => p.phase === phase);
              if (playbook) {
                usePhaseReviewStore.getState().beginReview(phase, playbook.reviewSteps);
              }
            }}
            variant="outline"
            size="sm"
            className="text-xs"
          >
            Skip to Review (DEBUG)
          </Button>
        )}
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
    </motion.div>
  );
}
