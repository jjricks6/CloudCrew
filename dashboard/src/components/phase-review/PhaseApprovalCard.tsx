/**
 * Phase approval card with formal approve/request changes gate.
 *
 * Displays two action buttons: "Approve & Continue" (moves to next phase)
 * and "Request Changes" (allows user to provide feedback).
 */

import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface PhaseApprovalCardProps {
  phaseName: string;
  onApprove: () => void;
  onRequestChanges: (feedback: string) => void;
  isLoading?: boolean;
}

export function PhaseApprovalCard({
  phaseName,
  onApprove,
  onRequestChanges,
  isLoading,
}: PhaseApprovalCardProps) {
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState("");

  const handleRequestChanges = useCallback(() => {
    if (!showFeedback) {
      setShowFeedback(true);
    } else if (feedback.trim().length > 0) {
      onRequestChanges(feedback.trim());
      setFeedback("");
      setShowFeedback(false);
    }
  }, [showFeedback, feedback, onRequestChanges]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="flex flex-col gap-4"
    >
      <div className="rounded-md border border-green-200 bg-green-50 p-4 dark:border-green-900 dark:bg-green-950">
        <h3 className="font-semibold text-green-900 dark:text-green-50">
          Ready to proceed?
        </h3>
        <p className="mt-1 text-sm text-green-800 dark:text-green-200">
          Review the {phaseName} phase summary and deliverables above. You can
          approve to move to the next phase or request changes.
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
    </motion.div>
  );
}
