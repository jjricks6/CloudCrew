import { ChatMessageList } from "@/components/chat/ChatMessageList";
import { ChatInput } from "@/components/chat/ChatInput";
import { useChatStore } from "@/state/stores/chatStore";
import { useChatHistory, useSendMessage } from "@/state/queries/useChatQueries";
import { useUploadFile } from "@/state/queries/useUploadQueries";
import { useProjectId } from "@/lib/useProjectId";

export function ChatPage() {
  const projectId = useProjectId();
  const isThinking = useChatStore((s) => s.isThinking);

  useChatHistory(projectId);
  const sendMessage = useSendMessage(projectId);
  const uploadFile = useUploadFile(projectId);

  const handleSend = (message: string) => {
    useChatStore.getState().addMessage({
      message_id: crypto.randomUUID(),
      role: "customer",
      content: message,
      timestamp: new Date().toISOString(),
    });
    sendMessage.mutate(message);
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

  return (
    <div className="flex h-[calc(100vh-120px)] flex-col">
      <ChatMessageList />
      <ChatInput
        onSend={handleSend}
        onUpload={handleUpload}
        disabled={isThinking || sendMessage.isPending}
        isUploading={uploadFile.isPending}
      />
    </div>
  );
}
