/**
 * Single-question card for the onboarding wizard.
 *
 * Displays the PM's streamed question text with a blinking cursor,
 * a text input area, an optional file upload zone, and a send button.
 * Only the current question is visible — previous Q&A pairs are not shown.
 */

import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { UploadZone } from "@/components/chat/UploadZone";
import { useOnboardingStore } from "@/state/stores/onboardingStore";
import type { OnboardingStep } from "@/lib/onboardingDemoTimeline";

interface OnboardingQuestionCardProps {
  step: OnboardingStep;
  questionText: string;
  isStreaming: boolean;
}

export function OnboardingQuestionCard({
  step,
  questionText,
  isStreaming,
}: OnboardingQuestionCardProps) {
  const [input, setInput] = useState("");
  const [uploadedFile, setUploadedFile] = useState<string | null>(null);
  const answerStep = useOnboardingStore((s) => s.answerStep);
  const advanceStep = useOnboardingStore((s) => s.advanceStep);

  const hasInput = step.placeholder !== "";
  const canSend = !isStreaming && input.trim().length > 0;

  const handleSend = useCallback(() => {
    if (!canSend) return;
    answerStep(input.trim());
    advanceStep();
    setInput("");
    setUploadedFile(null);
  }, [canSend, input, answerStep, advanceStep]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const handleUpload = useCallback((file: File) => {
    setUploadedFile(file.name);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="flex flex-col gap-4"
    >
      {/* PM question text with blinking cursor */}
      <div className="min-h-[80px] text-base leading-relaxed text-foreground">
        {questionText}
        {isStreaming && (
          <span className="ml-0.5 inline-block w-[2px] animate-pulse bg-primary">
            &nbsp;
          </span>
        )}
      </div>

      {/* Input area (hidden for no-input steps like SOW generation) */}
      {hasInput && (
        <>
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={step.placeholder}
            disabled={isStreaming}
            rows={3}
            className="resize-none"
          />

          {/* File upload zone (optional per step) */}
          {step.allowUpload && (
            <div className="space-y-1">
              <UploadZone onUpload={handleUpload} />
              {uploadedFile && (
                <p className="text-xs text-muted-foreground">
                  Attached: {uploadedFile}
                </p>
              )}
            </div>
          )}

          <div className="flex justify-end">
            <Button onClick={handleSend} disabled={!canSend} size="sm">
              Send
            </Button>
          </div>
        </>
      )}
    </motion.div>
  );
}
