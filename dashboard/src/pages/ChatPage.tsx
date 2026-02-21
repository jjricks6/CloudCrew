import { useRef } from "react";
import { ChatMessageList } from "@/components/chat/ChatMessageList";
import { ChatInput, type ChatInputHandle } from "@/components/chat/ChatInput";
import { useChatStore } from "@/state/stores/chatStore";
import { useAgentStore } from "@/state/stores/agentStore";
import { useChatHistory, useSendMessage } from "@/state/queries/useChatQueries";
import { useUploadFile } from "@/state/queries/useUploadQueries";
import {
  useApprovePhase,
  useRevisePhase,
  useRespondToInterrupt,
} from "@/state/queries/useApprovalQueries";
import { useProjectId } from "@/lib/useProjectId";
import { isDemoMode, DEMO_INTERRUPT } from "@/lib/demo";

export function ChatPage() {
  const projectId = useProjectId();
  const isThinking = useChatStore((s) => s.isThinking);
  const interrupt = useAgentStore((s) => s.pendingInterrupt);
  const inputHandleRef = useRef<ChatInputHandle | null>(null);

  useChatHistory(projectId);
  const sendMessage = useSendMessage(projectId);
  const uploadFile = useUploadFile(projectId);
  const respondToInterrupt = useRespondToInterrupt(projectId);
  const approvePhase = useApprovePhase(projectId);
  const revisePhase = useRevisePhase(projectId);

  const isBusy =
    isThinking ||
    sendMessage.isPending ||
    respondToInterrupt.isPending ||
    approvePhase.isPending ||
    revisePhase.isPending;

  const handleSend = (message: string) => {
    useChatStore.getState().addMessage({
      message_id: crypto.randomUUID(),
      role: "customer",
      content: message,
      timestamp: new Date().toISOString(),
    });

    if (interrupt) {
      respondToInterrupt.mutate({
        interruptId: interrupt.interrupt_id,
        response: message,
      });
    } else {
      sendMessage.mutate(message);
    }
  };

  const handleApprove = () => {
    useChatStore.getState().addMessage({
      message_id: crypto.randomUUID(),
      role: "customer",
      content: "Approved — looks good, continue to the next phase.",
      timestamp: new Date().toISOString(),
    });

    approvePhase.mutate(undefined, {
      onSuccess: () => {
        useAgentStore.getState().dismissApproval();
      },
    });
  };

  const handleRevise = (feedback: string) => {
    useChatStore.getState().addMessage({
      message_id: crypto.randomUUID(),
      role: "customer",
      content: feedback,
      timestamp: new Date().toISOString(),
    });

    revisePhase.mutate(feedback, {
      onSuccess: () => {
        useAgentStore.getState().dismissApproval();
      },
    });
  };

  const handleUpload = (file: File) => {
    uploadFile.mutate(
      { file },
      {
        onSuccess: (data) => {
          useChatStore.getState().addMessage({
            message_id: crypto.randomUUID(),
            role: "customer",
            content: `Uploaded: ${data.filename}`,
            timestamp: new Date().toISOString(),
          });
        },
      },
    );
  };

  const handleTypeOwn = () => {
    inputHandleRef.current?.focus();
  };

  // Quick-replies only for interrupt cards
  let quickReplies: readonly string[] | null = null;
  if (interrupt && isDemoMode(projectId)) {
    quickReplies = DEMO_INTERRUPT.quickReplies;
  }

  return (
    <div className="flex h-[calc(100vh-120px)] flex-col">
      <ChatMessageList
        quickReplies={quickReplies}
        onReply={handleSend}
        onApprove={handleApprove}
        onRevise={handleRevise}
        onTypeOwn={handleTypeOwn}
        replyDisabled={isBusy}
      />

      <ChatInput
        onSend={handleSend}
        onUpload={handleUpload}
        disabled={isBusy}
        isUploading={uploadFile.isPending}
        handleRef={inputHandleRef}
      />
    </div>
  );
}
