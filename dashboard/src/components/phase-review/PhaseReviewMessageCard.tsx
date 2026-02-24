/**
 * Phase review message card — displays PM opening/closing messages.
 *
 * Shows markdown content with streaming effect and optional Continue button.
 * Used for both opening message (with button) and closing message (without button).
 */

import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface PhaseReviewMessageCardProps {
  content: string;
  isStreaming: boolean;
  showContinue: boolean;
  onContinue: () => void;
}

export function PhaseReviewMessageCard({
  content,
  isStreaming,
  showContinue,
  onContinue,
}: PhaseReviewMessageCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="flex flex-col gap-4 h-full justify-center"
    >
      <div className="prose prose-sm dark:prose-invert max-w-none text-base leading-relaxed">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {isStreaming ? `${content}|` : content}
        </ReactMarkdown>
      </div>
      {isStreaming && (
        <style>{`
          .prose p:last-child::after {
            content: '|';
            animation: pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite;
            opacity: 0.7;
          }
          @keyframes pulse {
            0%, 100% { opacity: 0.7; }
            50% { opacity: 0.3; }
          }
        `}</style>
      )}

      {showContinue && (
        <div className="flex justify-end">
          <Button
            onClick={onContinue}
            disabled={isStreaming}
            size="sm"
          >
            Continue
          </Button>
        </div>
      )}
    </motion.div>
  );
}
