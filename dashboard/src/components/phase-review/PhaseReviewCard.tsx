/**
 * Phase review card for displaying the PM's walkthrough of phase completion.
 *
 * Shows the review text (what was done, key decisions) and artifacts
 * in a clean, scrollable format with a blinking cursor when streaming.
 */

import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface PhaseReviewCardProps {
  reviewText: string;
  artifactsText: string;
  isStreaming: boolean;
}

export function PhaseReviewCard({
  reviewText,
  artifactsText,
  isStreaming,
}: PhaseReviewCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="flex flex-col gap-6"
    >
      {/* Review text (what was done, key decisions) */}
      {reviewText && (
        <div className="flex flex-col gap-2">
          <div className="min-h-[100px] text-base leading-relaxed text-foreground">
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {reviewText}
              </ReactMarkdown>
            </div>
            {isStreaming && (
              <span className="ml-0.5 inline-block w-[2px] animate-pulse bg-primary">
                &nbsp;
              </span>
            )}
          </div>
        </div>
      )}

      {/* Artifacts section */}
      {artifactsText && (
        <div className="flex flex-col gap-2">
          <h4 className="font-semibold text-foreground">Deliverables</h4>
          <div className="max-h-[40vh] overflow-y-auto rounded-md border bg-muted/30 p-4">
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {artifactsText}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}
