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

  // PM messages — no bubble, plain text like Claude's responses
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-muted-foreground">
        Project Manager
      </p>
      <div className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
        {content}
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
