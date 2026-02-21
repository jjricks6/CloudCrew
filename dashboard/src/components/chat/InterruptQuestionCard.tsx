import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";

interface InterruptQuestionCardProps {
  phase: string;
  question: string;
  quickReplies: readonly string[] | null;
  onReply: (message: string) => void;
  onTypeOwn: () => void;
  disabled?: boolean;
}

export function InterruptQuestionCard({
  phase,
  question,
  quickReplies,
  onReply,
  onTypeOwn,
  disabled,
}: InterruptQuestionCardProps) {
  return (
    <div className="animate-interrupt-glow rounded-lg border border-yellow-500/50 bg-yellow-50/80 p-4 dark:bg-yellow-950/20">
      {/* Header */}
      <div className="mb-2 flex items-center gap-2">
        <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-yellow-500/20 text-yellow-700 dark:text-yellow-400">
          <PauseIcon />
        </span>
        <span className="text-xs font-semibold uppercase tracking-wide text-yellow-700 dark:text-yellow-400">
          Waiting for your input
        </span>
        <span className="rounded-full bg-yellow-500/15 px-2 py-0.5 text-[10px] font-medium text-yellow-700 dark:text-yellow-400">
          {phase} phase
        </span>
      </div>

      {/* Question rendered as markdown */}
      <div className="prose prose-sm dark:prose-invert max-w-none text-foreground prose-p:leading-relaxed prose-p:my-1">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{question}</ReactMarkdown>
      </div>

      {/* Quick replies */}
      {quickReplies && quickReplies.length > 0 && (
        <div className="mt-3 flex flex-col gap-1.5">
          {quickReplies.map((reply) => (
            <Button
              key={reply}
              variant="outline"
              size="sm"
              className="h-auto justify-start whitespace-normal border-yellow-500/30 bg-white/60 py-2 text-left text-xs hover:bg-yellow-100/60 dark:bg-yellow-950/30 dark:hover:bg-yellow-900/40"
              onClick={() => onReply(reply)}
              disabled={disabled}
            >
              {reply}
            </Button>
          ))}
          <Button
            variant="ghost"
            size="sm"
            className="h-auto justify-start py-2 text-left text-xs text-muted-foreground hover:text-foreground"
            onClick={onTypeOwn}
            disabled={disabled}
          >
            Type my own response...
          </Button>
        </div>
      )}
    </div>
  );
}

function PauseIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 16 16"
      fill="currentColor"
      className="h-3 w-3"
    >
      <path d="M5.75 3a.75.75 0 0 0-.75.75v8.5a.75.75 0 0 0 1.5 0v-8.5A.75.75 0 0 0 5.75 3Zm4.5 0a.75.75 0 0 0-.75.75v8.5a.75.75 0 0 0 1.5 0v-8.5a.75.75 0 0 0-.75-.75Z" />
    </svg>
  );
}
