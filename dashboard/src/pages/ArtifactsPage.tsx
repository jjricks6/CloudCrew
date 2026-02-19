import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ArtifactsPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Artifacts</h2>
      <Card className="min-h-[400px]">
        <CardHeader>
          <CardTitle className="text-sm font-medium">
            Project Deliverables
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Artifact browser and viewer will be implemented in M5f.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
