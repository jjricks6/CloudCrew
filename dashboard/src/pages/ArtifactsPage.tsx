import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ArtifactPreviewDialog } from "@/components/artifacts/ArtifactPreviewDialog";
import { downloadArtifact } from "@/components/artifacts/downloadArtifact";
import { useProjectDeliverables } from "@/state/queries/useProjectQueries";
import { useProjectId } from "@/lib/useProjectId";
import { isDemoMode, getArtifactContent } from "@/lib/demo";
import { PHASE_ORDER, type DeliverableItem } from "@/lib/types";

function statusVariant(
  status: DeliverableItem["status"],
): "default" | "secondary" | "destructive" {
  if (status === "COMPLETE") return "default";
  if (status === "IN_PROGRESS") return "secondary";
  return "destructive";
}

export function ArtifactsPage() {
  const projectId = useProjectId();
  const { data: deliverables, isLoading, isError, error } = useProjectDeliverables(projectId);
  const [selected, setSelected] = useState<DeliverableItem | null>(null);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold">Artifacts</h2>
        <div className="space-y-4">
          {[1, 2].map((i) => (
            <Skeleton key={i} className="h-32 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold">Artifacts</h2>
        <p className="text-sm text-destructive">
          Failed to load deliverables:{" "}
          {error instanceof Error ? error.message : "Unknown error"}
        </p>
      </div>
    );
  }

  // Group deliverables by phase in PHASE_ORDER
  const phases = PHASE_ORDER.filter(
    (phase) => deliverables?.[phase] && deliverables[phase].length > 0,
  );

  if (phases.length === 0) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold">Artifacts</h2>
        <Card className="min-h-[200px]">
          <CardContent className="flex items-center justify-center py-12">
            <p className="text-sm text-muted-foreground">
              No deliverables yet. Artifacts will appear here as agents produce
              them.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Artifacts</h2>

      {phases.map((phase) => (
        <Card key={phase}>
          <CardHeader>
            <CardTitle className="text-sm font-medium">{phase}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            {deliverables![phase].map((item) => (
              <div
                key={item.git_path}
                className="flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors hover:bg-muted"
              >
                <button
                  type="button"
                  onClick={() => setSelected(item)}
                  className="flex min-w-0 flex-1 items-center gap-3 text-left"
                >
                  <span className="flex-1 font-medium">{item.name}</span>
                  <span className="hidden font-mono text-xs text-muted-foreground sm:inline">
                    {item.git_path}
                  </span>
                  <Badge variant={statusVariant(item.status)}>
                    {item.status.replace("_", " ")}
                  </Badge>
                </button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 shrink-0 p-0"
                  title="Download"
                  onClick={(e) => {
                    e.stopPropagation();
                    const content = isDemoMode(projectId)
                      ? getArtifactContent(item.git_path)
                      : `# ${item.name}\n\nContent available when connected to live backend.`;
                    downloadArtifact(item.git_path, content);
                  }}
                >
                  <svg
                    className="h-4 w-4"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="7 10 12 15 17 10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
      ))}

      <ArtifactPreviewDialog
        artifact={selected}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}
