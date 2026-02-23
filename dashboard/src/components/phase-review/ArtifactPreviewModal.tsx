/**
 * Artifact preview modal — displays artifact details and download button.
 *
 * Shows the artifact name, git path, and version with a download button.
 */

import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { X, Download } from "lucide-react";

export interface Artifact {
  name: string;
  git_path: string;
  version: string;
}

interface ArtifactPreviewModalProps {
  artifact: Artifact;
  onClose: () => void;
}

export function ArtifactPreviewModal({
  artifact,
  onClose,
}: ArtifactPreviewModalProps) {
  const handleDownload = () => {
    // Create a simple text file with artifact info
    const content = `# ${artifact.name}

**Path:** ${artifact.git_path}
**Version:** ${artifact.version}

This artifact was delivered as part of the engagement.
`;

    const blob = new Blob([content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${artifact.name.toLowerCase().replace(/\s+/g, "-")}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <>
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 bg-black/50 z-40"
      />

      {/* Modal */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ duration: 0.2 }}
        className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-md"
      >
        <div className="rounded-lg border bg-card p-6 shadow-lg">
          {/* Header */}
          <div className="flex items-start justify-between gap-4 mb-4">
            <div className="flex-1">
              <h3 className="text-lg font-semibold">{artifact.name}</h3>
              <p className="text-sm text-muted-foreground mt-1">
                {artifact.git_path}
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Version */}
          <div className="mb-4 p-2 bg-muted rounded text-sm">
            <span className="text-muted-foreground">Version: </span>
            <span className="font-mono">{artifact.version}</span>
          </div>

          {/* Description */}
          <p className="text-sm text-muted-foreground mb-6">
            This artifact was delivered as part of the engagement. Click the
            download button to save a reference document.
          </p>

          {/* Actions */}
          <div className="flex gap-3">
            <Button onClick={handleDownload} size="sm" className="flex-1">
              <Download className="w-4 h-4 mr-2" />
              Download
            </Button>
            <Button onClick={onClose} variant="outline" size="sm" className="flex-1">
              Close
            </Button>
          </div>
        </div>
      </motion.div>
    </>
  );
}
