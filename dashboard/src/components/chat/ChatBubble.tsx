import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ChatBubbleProps {
  role: "customer" | "pm";
  content: string;
  timestamp?: string;
  isStreaming?: boolean;
}

export function ChatBubble({
  role,
  content,
  timestamp,
  isStreaming,
}: ChatBubbleProps) {
  if (role === "customer") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[70%] rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-primary-foreground">
          <p className="whitespace-pre-wrap text-sm leading-relaxed">
            {content}
          </p>
          {timestamp && (
            <p className="mt-1 text-right text-[10px] opacity-50">
              {new Date(timestamp).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </p>
          )}
        </div>
      </div>
    );
  }

  // PM messages — rendered with markdown like Claude's responses
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-muted-foreground">
        Project Manager
      </p>
      <div className="prose prose-sm dark:prose-invert max-w-none text-foreground prose-p:leading-relaxed prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-headings:mb-2 prose-headings:mt-3 prose-pre:bg-muted prose-pre:text-foreground">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        {isStreaming && (
          <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-foreground" />
        )}
      </div>
      {timestamp && (
        <p className="text-[10px] text-muted-foreground/50">
          {new Date(timestamp).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </p>
      )}
    </div>
  );
}
