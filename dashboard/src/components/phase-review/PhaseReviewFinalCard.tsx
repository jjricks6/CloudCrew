/**
 * Phase review final card — displays all review steps for final approval.
 *
 * Shows a scrollable summary of all review steps with user comments,
 * then two action buttons: "Approve & Continue" and "Request Changes".
 */

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ArtifactPreviewModal, type Artifact } from "./ArtifactPreviewModal";
import type { ReviewStep } from "@/state/stores/phaseReviewStore";

interface PhaseReviewFinalCardProps {
  steps: ReviewStep[];
  phaseName: string;
  onApprove: () => void;
  onRequestChanges: (feedback: string) => void;
  isLoading?: boolean;
}

export function PhaseReviewFinalCard({
  steps,
  phaseName,
  onApprove,
  onRequestChanges,
  isLoading,
}: PhaseReviewFinalCardProps) {
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null);

  const handleRequestChanges = useCallback(() => {
    if (!showFeedback) {
      setShowFeedback(true);
    } else if (feedback.trim().length > 0) {
      onRequestChanges(feedback.trim());
      setFeedback("");
      setShowFeedback(false);
    }
  }, [showFeedback, feedback, onRequestChanges]);

  // Extract artifacts from content (format: **Name** — description)
  const extractArtifacts = (content: string): Artifact[] => {
    const artifacts: Artifact[] = [];
    const lines = content.split("\n");
    for (const line of lines) {
      const match = line.match(/\*\*(.+?)\*\*\s*—\s*(.+)/);
      if (match) {
        artifacts.push({
          name: match[1],
          git_path: match[2],
          version: "v1.0",
        });
      }
    }
    return artifacts;
  };

  // Get all artifacts from all steps that are deliverables
  const allArtifacts = steps
    .filter((s) => s.type === "artifacts")
    .flatMap((s) => extractArtifacts(s.content));

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="flex flex-col gap-4"
    >
      <h3 className="text-lg font-semibold">
        {phaseName} Phase Review — Complete
      </h3>

      {/* Scrollable review summary */}
      <div className="max-h-[50vh] overflow-y-auto space-y-6 rounded-md border bg-muted/30 p-4">
        {steps.map((step) => (
          <div key={step.id} className="border-b last:border-0 pb-4 last:pb-0">
            <div className="flex items-center gap-2 mb-2">
              <h4 className="font-semibold text-sm">{step.title}</h4>
              <span className="inline-block rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900 dark:text-blue-100">
                {step.type === "summary"
                  ? "What We Did"
                  : step.type === "decisions"
                    ? "Key Decisions"
                    : "Deliverables"}
              </span>
            </div>

            <div className="prose prose-sm dark:prose-invert max-w-none mb-2">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {step.content}
              </ReactMarkdown>
            </div>

            {step.userComment && (
              <div className="rounded bg-yellow-50 p-2 text-xs dark:bg-yellow-950">
                <p className="font-medium text-yellow-900 dark:text-yellow-100">
                  Your comment:
                </p>
                <p className="text-yellow-800 dark:text-yellow-200">
                  {step.userComment}
                </p>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Approval notice */}
      <div className="rounded-md border border-green-200 bg-green-50 p-4 dark:border-green-900 dark:bg-green-950">
        <h4 className="font-semibold text-green-900 dark:text-green-50">
          Ready to proceed?
        </h4>
        <p className="mt-1 text-sm text-green-800 dark:text-green-200">
          Review the {phaseName} phase summary above. You can approve to move to
          the next phase or request changes.
        </p>
      </div>

      {showFeedback && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.3 }}
          className="flex flex-col gap-2"
        >
          <label className="text-sm font-medium">
            What would you like us to adjust?
          </label>
          <Textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="Describe the changes you'd like..."
            rows={3}
            className="resize-none"
            disabled={isLoading}
          />
        </motion.div>
      )}

      {/* Artifacts section */}
      {allArtifacts.length > 0 && (
        <div className="border-t pt-4">
          <h4 className="font-semibold text-sm mb-3">Available Artifacts</h4>
          <div className="space-y-2">
            {allArtifacts.map((artifact, idx) => (
              <button
                key={idx}
                onClick={() => setSelectedArtifact(artifact)}
                className="w-full flex items-center justify-between p-2 rounded border hover:bg-muted transition-colors text-left"
              >
                <div>
                  <p className="text-sm font-medium">{artifact.name}</p>
                  <p className="text-xs text-muted-foreground">{artifact.git_path}</p>
                </div>
                <span className="text-xs bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-100 px-2 py-1 rounded">
                  {artifact.version}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-3">
        <Button
          onClick={onApprove}
          disabled={isLoading}
          className="bg-green-600 hover:bg-green-700"
        >
          Approve & Continue
        </Button>
        <Button
          onClick={handleRequestChanges}
          variant="outline"
          disabled={isLoading}
        >
          {showFeedback ? "Submit Feedback" : "Request Changes"}
        </Button>
      </div>

      {/* Artifact preview modal */}
      <AnimatePresence>
        {selectedArtifact && (
          <ArtifactPreviewModal
            artifact={selectedArtifact}
            onClose={() => setSelectedArtifact(null)}
          />
        )}
      </AnimatePresence>
    </motion.div>
  );
}
