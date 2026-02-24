/**
 * Phase transition card — shows PM's closing statement before fading out.
 *
 * Displays a brief message from the PM indicating approval and transition to next phase.
 */

import { motion } from "framer-motion";

interface PhaseTransitionCardProps {
  phaseName: string;
  message: string;
}

export function PhaseTransitionCard({
  phaseName,
  message,
}: PhaseTransitionCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="flex flex-col gap-6 text-center"
    >
      <div className="space-y-2">
        <h3 className="text-2xl font-bold text-green-600 dark:text-green-400">
          Phase Complete ✓
        </h3>
        <p className="text-muted-foreground">{phaseName}</p>
      </div>

      <div className="rounded-lg border border-green-200 bg-green-50 p-6 dark:border-green-900 dark:bg-green-950">
        <p className="text-foreground leading-relaxed">{message}</p>
      </div>

      <p className="text-sm text-muted-foreground">
        Preparing next phase...
      </p>
    </motion.div>
  );
}
