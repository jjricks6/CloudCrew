import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { DeliverableItem } from "@/lib/types";
import { isDemoMode, getArtifactContent } from "@/lib/demo";
import { useProjectId } from "@/lib/useProjectId";
import { downloadArtifact } from "./downloadArtifact";

function statusVariant(
  status: DeliverableItem["status"],
): "default" | "secondary" | "destructive" {
  if (status === "COMPLETE") return "default";
  if (status === "IN_PROGRESS") return "secondary";
  return "destructive";
}

interface ArtifactPreviewDialogProps {
  artifact: DeliverableItem | null;
  onClose: () => void;
}

export function ArtifactPreviewDialog({
  artifact,
  onClose,
}: ArtifactPreviewDialogProps) {
  const projectId = useProjectId();

  const content = artifact
    ? isDemoMode(projectId)
      ? getArtifactContent(artifact.git_path)
      : `# ${artifact.name}\n\n*Content preview is available when connected to a live backend.*`
    : "";

  return (
    <Dialog open={!!artifact} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[80vh] overflow-y-auto sm:max-w-2xl">
        {artifact && (
          <>
            <DialogHeader>
              <div className="flex items-center gap-2">
                <DialogTitle>{artifact.name}</DialogTitle>
                <Badge variant={statusVariant(artifact.status)}>
                  {artifact.status.replace("_", " ")}
                </Badge>
              </div>
              <DialogDescription className="font-mono text-xs">
                {artifact.git_path}
              </DialogDescription>
            </DialogHeader>
            <div className="prose dark:prose-invert max-w-none text-sm">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {content}
              </ReactMarkdown>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                size="sm"
                onClick={() => downloadArtifact(artifact.git_path, content)}
              >
                <DownloadIcon />
                Download
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

function DownloadIcon() {
  return (
    <svg
      className="mr-1.5 h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  );
}
