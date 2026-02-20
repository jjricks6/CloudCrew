import { useEffect, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PhaseTimeline } from "@/components/PhaseTimeline";
import { ApprovalBanner } from "@/components/approval/ApprovalBanner";
import { useAgentStore } from "@/state/stores/agentStore";
import { useProjectStatus } from "@/state/queries/useProjectQueries";
import { useBoardTasks } from "@/state/queries/useBoardQueries";
import { KANBAN_COLUMNS } from "@/lib/types";
import { isDemoMode, DEMO_AGENTS, getDemoRecentActivity } from "@/lib/demo";

/** Short display name for agent roles. */
const AGENT_SHORT: Record<string, string> = {
  pm: "PM",
  sa: "SA",
  dev: "Dev",
  infra: "Infra",
  data: "Data",
  security: "Sec",
  qa: "QA",
};

function formatAgent(name: string): string {
  return AGENT_SHORT[name.toLowerCase()] ?? name;
}

/** Format an ISO timestamp into a short relative or absolute label. */
function formatTime(iso: string): string {
  const d = new Date(iso);
  const now = Date.now();
  const diffMs = now - d.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function DashboardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const wsStatus = useAgentStore((s) => s.wsStatus);
  const agents = useAgentStore((s) => s.agents);
  const interrupt = useAgentStore((s) => s.pendingInterrupt);

  const { data: project, isLoading: projectLoading } =
    useProjectStatus(projectId);
  const { data: tasks } = useBoardTasks(projectId);

  // Seed agent store with demo agents on mount (demo mode only)
  useEffect(() => {
    if (!isDemoMode(projectId)) return;
    const store = useAgentStore.getState();
    if (store.agents.length === 0) {
      for (const agent of DEMO_AGENTS) {
        store.addEvent({
          event: agent.status === "active" ? "agent_active" : "agent_idle",
          project_id: "demo",
          phase: agent.phase,
          agent_name: agent.agent_name,
          detail: agent.detail,
        });
      }
    }
  }, [projectId]);

  const taskCounts = KANBAN_COLUMNS.reduce(
    (acc, col) => {
      acc[col] = tasks?.filter((t) => t.status === col).length ?? 0;
      return acc;
    },
    {} as Record<string, number>,
  );

  const recentActivity = useMemo(() => {
    if (isDemoMode(projectId)) return getDemoRecentActivity();
    // In live mode, activity will come from WebSocket events (M5e).
    return [];
  }, [projectId]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h2 className="text-2xl font-bold">Project Overview</h2>
        <Badge variant={wsStatus === "connected" ? "default" : "outline"}>
          {wsStatus === "connected" ? "Live" : "Offline"}
        </Badge>
      </div>

      {/* Agent Question */}
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

      {/* Approval Gate */}
      <ApprovalBanner
        currentPhase={project?.current_phase}
        phaseStatus={project?.phase_status}
      />

      {/* Phase Timeline */}
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

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* Active Agents */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              Active Agents
            </CardTitle>
          </CardHeader>
          <CardContent>
            {agents.length > 0 ? (
              <ul className="space-y-1 text-sm">
                {agents.map((a) => (
                  <li key={a.agent_name}>
                    <button
                      type="button"
                      onClick={() => navigate("swarm")}
                      className="flex w-full items-center gap-2 rounded px-1 py-0.5 text-left transition-colors hover:bg-muted"
                    >
                      <span
                        className={`h-2 w-2 shrink-0 rounded-full ${
                          a.status === "active" ? "bg-green-500" : "bg-muted-foreground/40"
                        }`}
                      />
                      <span className="font-medium">{a.agent_name}</span>
                      <span className="text-muted-foreground">{a.status}</span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">
                No agent activity yet. Events will appear here when a phase is
                running.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Task Summary */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Board Tasks</CardTitle>
          </CardHeader>
          <CardContent>
            {tasks ? (
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-muted-foreground">Backlog</span>
                  <p className="text-lg font-semibold">{taskCounts.backlog}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">In Progress</span>
                  <p className="text-lg font-semibold">
                    {taskCounts.in_progress}
                  </p>
                </div>
                <div>
                  <span className="text-muted-foreground">Review</span>
                  <p className="text-lg font-semibold">{taskCounts.review}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Done</span>
                  <p className="text-lg font-semibold">{taskCounts.done}</p>
                </div>
              </div>
            ) : (
              <Skeleton className="h-16 w-full" />
            )}
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            {recentActivity.length > 0 ? (
              <ul className="space-y-2 text-sm">
                {recentActivity.map((item, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
                    <div className="min-w-0 flex-1">
                      <span className="font-medium">{formatAgent(item.agent)}</span>{" "}
                      <span className="text-muted-foreground line-clamp-1">
                        {item.action}
                      </span>
                    </div>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {formatTime(item.timestamp)}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">
                Activity timeline will be populated by WebSocket events.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
