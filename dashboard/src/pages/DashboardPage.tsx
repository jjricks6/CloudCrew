import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useAgentStore } from "@/state/stores/agentStore";

export function DashboardPage() {
  const wsStatus = useAgentStore((s) => s.wsStatus);
  const agents = useAgentStore((s) => s.agents);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h2 className="text-2xl font-bold">Project Overview</h2>
        <Badge variant={wsStatus === "connected" ? "default" : "outline"}>
          {wsStatus === "connected" ? "Live" : "Offline"}
        </Badge>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Active Agents</CardTitle>
          </CardHeader>
          <CardContent>
            {agents.length > 0 ? (
              <ul className="space-y-1 text-sm">
                {agents.map((a) => (
                  <li key={a.agent_name} className="flex items-center gap-2">
                    <span
                      className={`h-2 w-2 rounded-full ${
                        a.status === "active" ? "bg-green-500" : "bg-muted"
                      }`}
                    />
                    <span className="font-medium">{a.agent_name}</span>
                    <span className="text-muted-foreground">{a.status}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">
                No agent activity yet. Events will appear here when a phase is running.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Phase Progress</CardTitle>
          </CardHeader>
          <CardContent>
            <Skeleton className="h-4 w-3/4" />
            <p className="mt-3 text-sm text-muted-foreground">
              Phase tracking will be implemented in M5d.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <Skeleton className="h-4 w-full" />
            <Skeleton className="mt-2 h-4 w-5/6" />
            <p className="mt-3 text-sm text-muted-foreground">
              Activity timeline will be populated by WebSocket events.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
