import { useState, useMemo, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
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
import { useApprovePhase } from "@/state/queries/useApprovalQueries";
import { PHASE_PLAYBOOKS } from "@/lib/demoTimeline";
import { isDemoMode } from "@/lib/demo";
import type { AgentActivity } from "@/lib/types";

export function DashboardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const onboardingStatus = useOnboardingStore((s) => s.status);
  const isRealMode = useOnboardingStore((s) => s.isRealMode);
  const phaseReviewStatus = usePhaseReviewStore((s) => s.status);
  const wsStatus = useAgentStore((s) => s.wsStatus);
  const agents = useAgentStore((s) => s.agents);
  const interrupt = useAgentStore((s) => s.pendingInterrupt);
  const swarmEvents = useAgentStore((s) => s.swarmEvents);
  const activeHandoff = useAgentStore((s) => s.activeHandoff);
  const [selectedAgent, setSelectedAgent] = useState<AgentActivity | null>(null);

  const { data: project, isLoading: projectLoading } =
    useProjectStatus(projectId);

  const demo = isDemoMode(projectId);
  const approvePhase = useApprovePhase(projectId);
  const discoveryApprovedRef = useRef(false);
  const isRealDiscovery =
    !demo &&
    project?.current_phase === "DISCOVERY" &&
    project?.phase_status === "IN_PROGRESS";

  // Auto-start real-mode onboarding when entering Discovery phase
  useEffect(() => {
    const store = useOnboardingStore.getState();

    // If backend says Discovery IN_PROGRESS but store says "completed",
    // this is a new project — reset stale sessionStorage and restart.
    if (isRealDiscovery && store.status === "completed") {
      store.reset();
      store.startReal();
      return;
    }

    if (isRealDiscovery && !store.isRealMode && store.status !== "completed") {
      store.startReal();
    }
    // Complete real-mode onboarding when Discovery finishes
    if (
      store.isRealMode &&
      store.status !== "completed" &&
      project &&
      (project.current_phase !== "DISCOVERY" ||
        project.phase_status !== "IN_PROGRESS")
    ) {
      store.complete();
    }
  }, [isRealDiscovery, project]);

  // Auto-approve Discovery phase — the user already approved the SOW during
  // onboarding, so there's nothing to review. Fire the approve API once to
  // tell the backend to advance to Architecture.
  useEffect(() => {
    if (
      project?.current_phase === "DISCOVERY" &&
      project.phase_status === "AWAITING_APPROVAL" &&
      !discoveryApprovedRef.current &&
      !approvePhase.isPending
    ) {
      discoveryApprovedRef.current = true;
      approvePhase.mutate(undefined, {
        onSuccess: () => {
          useAgentStore.getState().dismissApproval();
        },
        onError: () => {
          // Allow retry on next render cycle
          discoveryApprovedRef.current = false;
        },
      });
    }
  }, [project, approvePhase]);

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
      project.current_phase !== "DISCOVERY" &&
      (phaseReviewStatus === "not_started" || phaseReviewStatus === "completed")
    ) {
      return {
        type: "approval" as const,
        message: `The ${project.current_phase} phase is ready for your review.`,
        buttonLabel: "Review",
        onAction: () => {
          if (demo) {
            // Demo mode: use startOpeningMessage so demo engine can stream
            // character-by-character (beginReview pre-populates content)
            const playbook = PHASE_PLAYBOOKS.find(
              (p) => p.phase === project.current_phase
            );
            if (playbook && project.current_phase) {
              usePhaseReviewStore
                .getState()
                .startOpeningMessage(
                  project.current_phase,
                  playbook.reviewMessages.opening,
                  playbook.reviewMessages.closing,
                  playbook.phaseSummaryPath
                );
            }
          } else if (project.current_phase) {
            // Real mode: use persisted messages from API if available,
            // otherwise WebSocket streaming will fill them in
            const opening = project.review_opening_message ?? "";
            const closing = project.review_closing_message ?? "";
            const summaryPath = `docs/phase-summaries/${project.current_phase.toLowerCase()}.md`;
            usePhaseReviewStore
              .getState()
              .beginReview(project.current_phase, opening, closing, summaryPath);
          }
        },
      };
    }
    return null;
  }, [interrupt, project, phaseReviewStatus, navigate, demo]);

  // Show onboarding wizard for demo mode or real Discovery phase
  if (
    onboardingStatus !== "completed" &&
    (demo || isRealDiscovery || isRealMode)
  ) {
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
      <div className="flex items-center gap-2 md:gap-3">
        <h2 className="text-lg font-bold md:text-2xl">
          {project?.project_name ?? "Project"}
        </h2>
        <Badge variant={wsStatus === "connected" ? "default" : "outline"}>
          {wsStatus === "connected" ? "Live" : "Offline"}
        </Badge>
      </div>

      {/* Phase Progress */}
      <Card className="py-3 gap-2 md:py-6 md:gap-6">
        <CardHeader className="px-3 md:px-6">
          <CardTitle className="text-sm font-medium">Phase Progress</CardTitle>
        </CardHeader>
        <CardContent className="px-3 md:px-6">
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

      {/* Swarm (center) + Activity (right on desktop, below on mobile) */}
      <div className="flex flex-col gap-4 md:h-[calc(100vh-21rem)] md:min-h-[300px] md:flex-row md:gap-6">
        {/* Swarm visualization */}
        <div className="relative h-[420px] flex-1 overflow-visible md:h-full">
          <SwarmVisualization
            agents={agents}
            phase={project?.current_phase}
            activeHandoff={activeHandoff}
            onAgentClick={setSelectedAgent}
            notification={centerNotification}
          />
        </div>

        {/* Activity feed */}
        <div className="flex w-full flex-col md:max-h-none md:w-72 md:shrink-0 md:overflow-hidden">
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
