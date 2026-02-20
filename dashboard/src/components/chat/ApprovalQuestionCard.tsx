import { useState } from "react";
import { useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface ApprovalQuestionCardProps {
  phase: string;
  question: string;
  onApprove: () => void;
  onRevise: (feedback: string) => void;
  disabled?: boolean;
}

export function ApprovalQuestionCard({
  phase,
  question,
  onApprove,
  onRevise,
  disabled,
}: ApprovalQuestionCardProps) {
  const navigate = useNavigate();
  const [feedback, setFeedback] = useState("");

  const handleSubmitFeedback = () => {
    if (!feedback.trim()) return;
    onRevise(feedback.trim());
    setFeedback("");
  };

  return (
    <div className="animate-interrupt-glow rounded-lg border border-yellow-500/50 bg-yellow-50/80 p-4 dark:bg-yellow-950/20">
      {/* Header */}
      <div className="mb-2 flex items-center gap-2">
        <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-yellow-500/20 text-yellow-700 dark:text-yellow-400">
          <CheckCircleIcon />
        </span>
        <span className="text-xs font-semibold uppercase tracking-wide text-yellow-700 dark:text-yellow-400">
          Phase Review
        </span>
        <span className="rounded-full bg-yellow-500/15 px-2 py-0.5 text-[10px] font-medium text-yellow-700 dark:text-yellow-400">
          {phase} phase
        </span>
      </div>

      {/* Question rendered as markdown */}
      <div className="prose prose-sm dark:prose-invert max-w-none text-foreground prose-p:leading-relaxed prose-p:my-1">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{question}</ReactMarkdown>
      </div>

      {/* Action buttons */}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="border-yellow-500/30 bg-white/60 text-xs hover:bg-yellow-100/60 dark:bg-yellow-950/30 dark:hover:bg-yellow-900/40"
          onClick={() => navigate("../artifacts")}
        >
          Review Artifacts
        </Button>
        <Button
          size="sm"
          className="bg-green-600 text-xs text-white hover:bg-green-700"
          onClick={onApprove}
          disabled={disabled}
        >
          Approve
        </Button>
      </div>

      {/* Feedback textarea */}
      <div className="mt-3 space-y-2">
        <Textarea
          placeholder="Have feedback or questions? Type here..."
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          rows={2}
          className="border-yellow-500/30 bg-white/60 text-sm placeholder:text-muted-foreground/60 dark:bg-yellow-950/30"
        />
        {feedback.trim() && (
          <Button
            variant="outline"
            size="sm"
            className="border-yellow-500/30 bg-white/60 text-xs hover:bg-yellow-100/60 dark:bg-yellow-950/30 dark:hover:bg-yellow-900/40"
            onClick={handleSubmitFeedback}
            disabled={disabled}
          >
            Send Feedback
          </Button>
        )}
      </div>
    </div>
  );
}

function CheckCircleIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 16 16"
      fill="currentColor"
      className="h-3 w-3"
    >
      <path
        fillRule="evenodd"
        d="M8 15A7 7 0 1 0 8 1a7 7 0 0 0 0 14Zm3.844-8.791a.75.75 0 0 0-1.188-.918l-3.7 4.79-1.649-1.833a.75.75 0 1 0-1.114 1.004l2.25 2.5a.75.75 0 0 0 1.15-.043l4.25-5.5Z"
        clipRule="evenodd"
      />
    </svg>
  );
}
