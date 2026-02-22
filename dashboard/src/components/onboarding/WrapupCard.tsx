/**
 * Wrap-up card — PM's farewell message after SOW acceptance.
 *
 * Displays the streamed wrap-up text explaining how the project proceeds,
 * with a single "Continue to Dashboard" button that completes onboarding.
 */

import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { useOnboardingStore } from "@/state/stores/onboardingStore";

interface WrapupCardProps {
  messageText: string;
  isStreaming: boolean;
}

export function WrapupCard({ messageText, isStreaming }: WrapupCardProps) {
  const complete = useOnboardingStore((s) => s.complete);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="flex flex-col gap-4"
    >
      {/* PM message with blinking cursor while streaming */}
      <div className="min-h-[120px] whitespace-pre-line text-base leading-relaxed text-foreground">
        {messageText}
        {isStreaming && (
          <span className="ml-0.5 inline-block w-[2px] animate-pulse bg-primary">
            &nbsp;
          </span>
        )}
      </div>

      {/* Continue button — visible only after streaming completes */}
      {!isStreaming && messageText.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.4 }}
          className="flex justify-end"
        >
          <Button onClick={complete}>Continue to Dashboard</Button>
        </motion.div>
      )}
    </motion.div>
  );
}
