import { useEffect, useRef } from "react";
import { useChatStore } from "@/state/stores/chatStore";
import { ChatBubble } from "./ChatBubble";
import { ThinkingIndicator } from "./ThinkingIndicator";

export function ChatMessageList() {
  const messages = useChatStore((s) => s.messages);
  const isThinking = useChatStore((s) => s.isThinking);
  const streamingContent = useChatStore((s) => s.streamingContent);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent, isThinking]);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-3xl space-y-4 px-4 py-6">
        {messages.length === 0 && !isThinking && !streamingContent && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <p className="text-sm text-muted-foreground">
              Start a conversation with your Project Manager.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <ChatBubble
            key={msg.message_id}
            role={msg.role}
            content={msg.content}
            timestamp={msg.timestamp}
          />
        ))}

        {/* Streaming PM response (token-by-token) */}
        {streamingContent && (
          <ChatBubble role="pm" content={streamingContent} isStreaming />
        )}

        {/* Thinking indicator (before first chunk arrives) */}
        {isThinking && !streamingContent && <ThinkingIndicator />}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
