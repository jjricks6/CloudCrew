/**
 * Phase review step card — displays one step of the review with optional user comment.
 *
 * Shows the PM's streamed content for a single step (summary, decisions, artifacts)
 * with a comment area and "Continue" button at the bottom.
 */

import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ReviewStep } from "@/state/stores/phaseReviewStore";

interface PhaseReviewStepCardProps {
  step: ReviewStep;
  currentContent: string;
  isStreaming: boolean;
  onAddComment: (comment: string) => void;
  onContinue: () => void;
  isLoading?: boolean;
}

export function PhaseReviewStepCard({
  step,
  currentContent,
  isStreaming,
  onAddComment,
  onContinue,
  isLoading,
}: PhaseReviewStepCardProps) {
  const [comment, setComment] = useState(step.userComment || "");

  const handleContinue = useCallback(() => {
    if (comment.trim()) {
      onAddComment(comment.trim());
    }
    onContinue();
  }, [comment, onAddComment, onContinue]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="flex flex-col gap-4"
    >
      {/* Step title and type badge */}
      <div className="flex items-center gap-3">
        <h3 className="text-lg font-semibold">{step.title}</h3>
        <span className="inline-block rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-700 dark:bg-blue-900 dark:text-blue-100">
          {step.type === "summary"
            ? "What We Did"
            : step.type === "decisions"
              ? "Key Decisions"
              : "Deliverables"}
        </span>
      </div>

      {/* Content (streamed or full) */}
      <div className="min-h-[120px] text-base leading-relaxed text-foreground prose prose-sm dark:prose-invert max-w-none">
        <div className="inline">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {currentContent}
          </ReactMarkdown>
          {isStreaming && (
            <span className="animate-pulse bg-primary">|</span>
          )}
        </div>
      </div>

      {/* User comment area */}
      <div className="flex flex-col gap-2">
        <label className="text-sm font-medium text-muted-foreground">
          Any questions or feedback? (optional)
        </label>
        <Textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Share your thoughts about this section..."
          rows={2}
          className="resize-none"
          disabled={isLoading || isStreaming}
        />
      </div>

      {/* Continue button */}
      <div className="flex justify-end">
        <Button
          onClick={handleContinue}
          disabled={isLoading || isStreaming}
          size="sm"
        >
          {isLoading ? "Processing..." : "Continue"}
        </Button>
      </div>
    </motion.div>
  );
}
