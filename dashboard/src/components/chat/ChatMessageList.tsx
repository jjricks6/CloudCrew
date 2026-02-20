import { useEffect, useRef } from "react";
import { useChatStore } from "@/state/stores/chatStore";
import { useAgentStore } from "@/state/stores/agentStore";
import { ChatBubble } from "./ChatBubble";
import { InterruptQuestionCard } from "./InterruptQuestionCard";
import { ApprovalQuestionCard } from "./ApprovalQuestionCard";
import { ThinkingIndicator } from "./ThinkingIndicator";

interface ChatMessageListProps {
  quickReplies?: readonly string[] | null;
  onReply?: (message: string) => void;
  onApprove?: () => void;
  onRevise?: (feedback: string) => void;
  onTypeOwn?: () => void;
  replyDisabled?: boolean;
}

export function ChatMessageList({
  quickReplies,
  onReply,
  onApprove,
  onRevise,
  onTypeOwn,
  replyDisabled,
}: ChatMessageListProps) {
  const messages = useChatStore((s) => s.messages);
  const isThinking = useChatStore((s) => s.isThinking);
  const streamingContent = useChatStore((s) => s.streamingContent);
  const interrupt = useAgentStore((s) => s.pendingInterrupt);
  const approval = useAgentStore((s) => s.pendingApproval);
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

        {messages.map((msg) => {
          // Interrupt messages get the special yellow card treatment
          if (
            msg.message_id.startsWith("interrupt-") &&
            interrupt &&
            onReply &&
            onTypeOwn
          ) {
            return (
              <InterruptQuestionCard
                key={msg.message_id}
                phase={interrupt.phase}
                question={interrupt.question}
                quickReplies={quickReplies ?? null}
                onReply={onReply}
                onTypeOwn={onTypeOwn}
                disabled={replyDisabled}
              />
            );
          }

          // Approval messages get the approval card with approve/revise controls
          if (
            msg.message_id.startsWith("approval-") &&
            approval &&
            onApprove &&
            onRevise
          ) {
            return (
              <ApprovalQuestionCard
                key={msg.message_id}
                phase={approval.phase}
                question={msg.content}
                onApprove={onApprove}
                onRevise={onRevise}
                disabled={replyDisabled}
              />
            );
          }

          return (
            <ChatBubble
              key={msg.message_id}
              role={msg.role}
              content={msg.content}
              timestamp={msg.timestamp}
            />
          );
        })}

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
