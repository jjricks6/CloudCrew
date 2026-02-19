import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function SwarmPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Swarm Visualization</h2>
      <Card className="h-[calc(100vh-220px)]">
        <CardHeader>
          <CardTitle className="text-sm font-medium">
            Agent Swarm — Live View
          </CardTitle>
        </CardHeader>
        <CardContent className="flex h-full items-center justify-center">
          <p className="text-muted-foreground">
            Animated swarm visualization will be implemented in M5e.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
