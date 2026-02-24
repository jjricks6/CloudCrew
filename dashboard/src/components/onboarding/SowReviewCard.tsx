/**
 * SOW review card with formal accept/revise approval gate.
 *
 * Displays the generated Statement of Work as rendered markdown with
 * two action buttons: "Accept SOW" (completes onboarding) and
 * "Request Changes" (returns to the last question for refinement).
 */

import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { useOnboardingStore } from "@/state/stores/onboardingStore";

interface SowReviewCardProps {
  sowContent: string;
}

export function SowReviewCard({ sowContent }: SowReviewCardProps) {
  const enterWrapup = useOnboardingStore((s) => s.enterWrapup);
  const requestRevision = useOnboardingStore((s) => s.requestRevision);

  const handleAccept = () => {
    enterWrapup();
  };

  const handleRevise = () => {
    requestRevision();
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="flex flex-col gap-4"
    >
      <h3 className="text-lg font-semibold">Statement of Work</h3>
      <p className="text-sm text-muted-foreground">
        Please review the proposed scope, timeline, and team composition below.
      </p>

      {/* Scrollable SOW content */}
      <div className="max-h-[50vh] overflow-y-auto rounded-md border bg-muted/30 p-4">
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {sowContent}
          </ReactMarkdown>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex gap-3">
        <Button onClick={handleAccept} className="bg-green-600 hover:bg-green-700">
          Accept SOW
        </Button>
        <Button onClick={handleRevise} variant="outline">
          Request Changes
        </Button>
      </div>
    </motion.div>
  );
}
