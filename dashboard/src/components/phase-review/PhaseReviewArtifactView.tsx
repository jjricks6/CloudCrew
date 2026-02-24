/**
 * Phase review artifact view — main review screen with artifacts + chat + approval.
 *
 * Two modes:
 * 1. Artifact Review: Top shows artifact selection + document preview, bottom shows compact chat
 * 2. Chat Conversation: Full screen chat when user asks questions, can return to artifacts
 *
 * Users can:
 * - Select and review all artifacts (defaults to Phase Summary)
 * - Ask PM questions via chat (enters conversation mode)
 * - Download artifacts
 * - Approve or request changes
 */

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Download, Send, ArrowLeft } from "lucide-react";
import { fetchArtifactContent } from "@/lib/api";
import { isDemoMode, getArtifactContent } from "@/lib/demo";
import type { ChatMessage } from "@/state/stores/phaseReviewStore";

interface DeliverableItem {
  name: string;
  git_path: string;
  version: string;
}

interface Props {
  projectId?: string;
  phaseName: string;
  phaseSummaryPath?: string;
  artifacts: DeliverableItem[];
  chatHistory: ChatMessage[];
  currentChatContent: string;
  isChatStreaming: boolean;
  onSendMessage: (message: string) => void;
  onApprove: () => void;
  isLoading: boolean;
}

interface Document {
  id: string;
  name: string;
  path: string;
}

export function PhaseReviewArtifactView({
  projectId,
  phaseName,
  phaseSummaryPath,
  artifacts,
  chatHistory,
  currentChatContent,
  isChatStreaming,
  onSendMessage,
  onApprove,
  isLoading,
}: Props) {
  const [selectedDocId, setSelectedDocId] = useState("phase-summary");
  const [docContent, setDocContent] = useState<string>("");
  const [isLoadingDoc, setIsLoadingDoc] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [inChatMode, setInChatMode] = useState(false);

  // Build document list: Phase Summary (if available) + all artifacts
  const documents: Document[] = [
    ...(phaseSummaryPath
      ? [{ id: "phase-summary", name: "Phase Summary", path: phaseSummaryPath }]
      : []),
    ...artifacts.map((a, idx) => ({
      id: `artifact-${idx}`,
      name: a.name,
      path: a.git_path,
    })),
  ];

  const selectedDoc = documents.find((d) => d.id === selectedDocId) || documents[0];

  // Fetch selected document content
  useEffect(() => {
    if (!selectedDoc || !projectId) return;

    let cancelled = false;

    const load = async () => {
      setIsLoadingDoc(true);

      if (isDemoMode(projectId)) {
        // Demo mode: use canned content
        const content = getArtifactContent(selectedDoc.path);
        if (!cancelled) {
          setDocContent(content);
          setIsLoadingDoc(false);
        }
      } else {
        // Real mode: fetch from API
        try {
          const data = await fetchArtifactContent(projectId, selectedDoc.path);
          if (!cancelled) {
            setDocContent(data.exists ? data.content : "Document not found.");
          }
        } catch (err) {
          if (!cancelled) {
            setDocContent(`Error loading document: ${err instanceof Error ? err.message : "Unknown error"}`);
          }
        } finally {
          if (!cancelled) {
            setIsLoadingDoc(false);
          }
        }
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, [selectedDoc, projectId]);

  const handleSendChat = () => {
    if (chatInput.trim()) {
      onSendMessage(chatInput.trim());
      setChatInput("");
      // Enter chat mode when user sends a message
      setInChatMode(true);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendChat();
    }
  };

  const handleDownload = (doc: Document) => {
    const content = `# ${doc.name}\n\n**Path:** ${doc.path}\n\nThis artifact was delivered as part of the engagement.\n`;
    const blob = new Blob([content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${doc.name.toLowerCase().replace(/\s+/g, "-")}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col min-h-0 flex-1 gap-4"
    >
      <h3 className="text-lg font-semibold">{phaseName} review</h3>

      <AnimatePresence mode="wait">
        {/* Artifact Review Mode */}
        {!inChatMode && (
          <motion.div
            key="artifacts"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col min-h-0 flex-1 gap-4"
          >
            {/* Top: Artifacts + Preview (flex-1 grows to fill, input/buttons stay at bottom) */}
            <div className="flex-1 min-h-0 flex flex-col md:flex-row gap-4">
              {/* Artifact buttons */}
              <div className="flex md:flex-col gap-2 overflow-x-auto md:overflow-y-auto md:w-48 flex-shrink-0 pb-2 md:pb-0">
                {documents.map((doc) => (
                  <button
                    key={doc.id}
                    onClick={() => setSelectedDocId(doc.id)}
                    className={`px-3 py-2 rounded text-sm font-medium whitespace-nowrap transition-colors ${
                      doc.id === selectedDocId
                        ? "bg-blue-600 text-white dark:bg-blue-700"
                        : "bg-muted text-muted-foreground hover:bg-muted/80 dark:hover:bg-muted/60"
                    }`}
                  >
                    {doc.name}
                  </button>
                ))}
              </div>

              {/* Document preview */}
              <div className="flex-1 min-h-0 flex flex-col rounded-md border bg-muted/30 overflow-hidden">
                <div className="border-b p-3 flex items-center justify-between bg-muted/50 gap-3 flex-shrink-0">
                  <h4 className="font-semibold text-sm">{selectedDoc.name}</h4>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDownload(selectedDoc)}
                    className="flex-shrink-0"
                  >
                    <Download className="w-4 h-4 mr-1.5" />
                    Download
                  </Button>
                </div>
                <div className="flex-1 overflow-y-auto p-4 min-h-0">
                  {isLoadingDoc ? (
                    <p className="text-sm text-muted-foreground">Loading...</p>
                  ) : (
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {docContent}
                      </ReactMarkdown>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Bottom: Chat Input + Approval (flex-shrink-0 stays at bottom) */}
            <div className="flex-shrink-0 flex flex-col gap-2 rounded-md border bg-muted/30 p-4">
              {/* Chat input */}
              <div className="flex gap-2 flex-shrink-0">
                <Textarea
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="Ask a question or request a change..."
                  disabled={isChatStreaming || isLoading}
                  rows={2}
                  className="flex-1 text-sm resize-none"
                />
                <Button
                  onClick={handleSendChat}
                  disabled={!chatInput.trim() || isChatStreaming || isLoading}
                  size="sm"
                  className="flex-shrink-0 h-full"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>

              {/* Approval buttons */}
              <div className="flex gap-2 flex-shrink-0">
                <Button
                  onClick={onApprove}
                  disabled={isLoading || isChatStreaming}
                  className="bg-green-600 hover:bg-green-700 text-sm"
                  size="sm"
                >
                  Approve & Continue
                </Button>
              </div>
            </div>
          </motion.div>
        )}

        {/* Chat Conversation Mode */}
        {inChatMode && (
          <motion.div
            key="chat"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col min-h-0 flex-1 gap-2"
          >
            <div className="flex-1 min-h-0 flex flex-col rounded-md border bg-muted/30 overflow-hidden">
              {/* Chat header */}
              <div className="border-b p-3 bg-muted/50 flex-shrink-0">
                <h4 className="font-semibold text-sm">Chat with PM</h4>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Ask questions about the phase and deliverables
                </p>
              </div>

              {/* Chat messages */}
              <div className="flex-1 overflow-y-auto p-3 space-y-2 min-h-0">
                {chatHistory.map((msg) => (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-xs rounded-lg px-3 py-2 text-xs ${
                        msg.role === "user"
                          ? "bg-blue-600 text-white dark:bg-blue-700"
                          : "bg-muted text-foreground"
                      }`}
                    >
                      {msg.content}
                    </div>
                  </motion.div>
                ))}
                {currentChatContent && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex justify-start"
                  >
                    <div className="max-w-xs rounded-lg px-3 py-2 text-xs bg-muted text-foreground">
                      {currentChatContent}
                      {isChatStreaming && <span className="animate-pulse">|</span>}
                    </div>
                  </motion.div>
                )}
              </div>

              {/* Chat input */}
              <div className="border-t p-3 bg-muted/50 flex-shrink-0 flex gap-2">
                <Input
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="Type your message..."
                  disabled={isChatStreaming || isLoading}
                  className="flex-1 text-sm h-9"
                />
                <Button
                  onClick={handleSendChat}
                  disabled={!chatInput.trim() || isChatStreaming || isLoading}
                  size="sm"
                  className="h-9"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </div>

            {/* Return to artifacts button */}
            <Button
              onClick={() => setInChatMode(false)}
              variant="outline"
              className="flex-shrink-0 h-9"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Phase Review
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
