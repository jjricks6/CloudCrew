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
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import { Download, Send, ArrowLeft, ExternalLink } from "lucide-react";
import { PhaseApprovalCard } from "./PhaseApprovalCard";
import { fetchArtifactContent, fetchArtifactList, post } from "@/lib/api";
import type { ArtifactListItem } from "@/lib/api";
import { isDemoMode, getArtifactContent, getDemoArtifactList } from "@/lib/demo";
import type { ChatMessage } from "@/state/stores/phaseReviewStore";

interface Props {
  projectId?: string;
  phaseName: string;
  chatHistory: ChatMessage[];
  currentChatContent: string;
  isChatStreaming: boolean;
  onSendMessage: (message: string) => void;
  onApprove: () => void;
  onRequestChanges: (feedback: string) => void;
  isLoading: boolean;
  gitRepoUrl?: string;
}

interface Document {
  id: string;
  name: string;
  path: string;
}

export function PhaseReviewArtifactView({
  projectId,
  phaseName,
  chatHistory,
  currentChatContent,
  isChatStreaming,
  onSendMessage,
  onApprove,
  onRequestChanges,
  isLoading,
  gitRepoUrl,
}: Props) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>("");
  const [docContent, setDocContent] = useState<string>("");
  const [isLoadingDoc, setIsLoadingDoc] = useState(false);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [chatInput, setChatInput] = useState("");
  const [inChatMode, setInChatMode] = useState(false);

  // Fetch artifact list from S3 via API (or demo data)
  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;

    const loadList = async () => {
      setIsLoadingList(true);
      try {
        let items: ArtifactListItem[];
        if (isDemoMode(projectId)) {
          items = getDemoArtifactList(phaseName);
        } else {
          items = await fetchArtifactList(projectId);
        }
        if (!cancelled) {
          const docs = items.map((item, idx) => ({
            id: `artifact-${idx}`,
            name: item.name,
            path: item.path,
          }));
          setDocuments(docs);
          // Auto-select first document
          if (docs.length > 0 && !selectedDocId) {
            setSelectedDocId(docs[0].id);
          }
        }
      } catch (err) {
        console.error("Failed to load artifact list:", err);
      } finally {
        if (!cancelled) setIsLoadingList(false);
      }
    };
    loadList();

    return () => { cancelled = true; };
  }, [projectId, phaseName]); // eslint-disable-line react-hooks/exhaustive-deps

  const selectedDoc = documents.find((d) => d.id === selectedDocId) || documents[0];

  // Fetch selected document content — use selectedDoc.path (a string) as the
  // dependency instead of the selectedDoc object to avoid infinite re-renders
  // (documents array is rebuilt each render, creating new object references).
  const selectedPath = selectedDoc?.path;
  useEffect(() => {
    if (!selectedPath || !projectId) return;

    let cancelled = false;

    const load = async () => {
      setIsLoadingDoc(true);

      if (isDemoMode(projectId)) {
        // Demo mode: use canned content
        const content = getArtifactContent(selectedPath);
        if (!cancelled) {
          setDocContent(content);
          setIsLoadingDoc(false);
        }
      } else {
        // Real mode: fetch from API
        try {
          const data = await fetchArtifactContent(projectId, selectedPath);
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
  }, [selectedPath, projectId]);

  const handleSendChat = async () => {
    if (chatInput.trim()) {
      const message = chatInput.trim();
      setChatInput("");
      // Enter chat mode when user sends a message
      setInChatMode(true);

      // Add user message to phaseReviewStore chat history
      onSendMessage(message);

      if (!isDemoMode(projectId) && projectId) {
        // Real mode: call chat API — PM response streams via WebSocket
        try {
          await post(`/projects/${projectId}/chat`, { message });
        } catch (error) {
          console.error("Error sending chat message:", error);
        }
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendChat();
    }
  };

  const handleDownload = (doc: Document) => {
    // Use the currently loaded content if we're viewing this document,
    // otherwise fall back to a placeholder with the path.
    const content =
      selectedDoc?.path === doc.path && docContent
        ? docContent
        : `# ${doc.name}\n\n**Path:** ${doc.path}\n\nContent not yet loaded. Select this artifact to preview it first.\n`;
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
      className="flex flex-col min-h-0 min-w-0 w-full flex-1 gap-2 md:gap-4 overflow-hidden"
    >
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-base font-semibold md:text-lg">{phaseName} review</h3>
        {gitRepoUrl && (
          <a
            href={gitRepoUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-950 transition-colors md:gap-1.5 md:px-3 md:py-1.5 md:text-sm"
          >
            <ExternalLink className="w-3.5 h-3.5 md:w-4 md:h-4" />
            <span className="hidden sm:inline">View Code on</span> GitHub
          </a>
        )}
      </div>

      <AnimatePresence mode="wait">
        {/* Artifact Review Mode */}
        {!inChatMode && (
          <motion.div
            key="artifacts"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col min-h-0 min-w-0 w-full flex-1 gap-2 md:gap-4"
          >
            {/* Top: Artifacts + Preview (flex-1 grows to fill, input/buttons stay at bottom) */}
            <div className="flex-1 min-h-0 flex flex-col md:flex-row gap-2 md:gap-4">
              {/* Artifact buttons — compact horizontal tabs on mobile */}
              <div className="flex md:flex-col gap-1.5 md:gap-2 overflow-x-auto md:overflow-y-auto md:w-48 flex-shrink-0 pb-1 md:pb-0">
                {isLoadingList ? (
                  <p className="text-xs text-muted-foreground px-2 py-1">Loading...</p>
                ) : documents.length === 0 ? (
                  <p className="text-xs text-muted-foreground px-2 py-1">No artifacts found</p>
                ) : (
                  documents.map((doc) => (
                    <button
                      key={doc.id}
                      onClick={() => setSelectedDocId(doc.id)}
                      className={`px-2 py-1 md:px-3 md:py-2 rounded text-xs md:text-sm font-medium whitespace-nowrap transition-colors ${
                        doc.id === selectedDocId
                          ? "bg-blue-600 text-white dark:bg-blue-700"
                          : "bg-muted text-muted-foreground hover:bg-muted/80 dark:hover:bg-muted/60"
                      }`}
                    >
                      {doc.name}
                    </button>
                  ))
                )}
              </div>

              {/* Document preview */}
              <div className="flex-1 min-h-0 flex flex-col rounded-md border bg-muted/30 overflow-hidden">
                {selectedDoc ? (
                  <>
                    <div className="border-b px-2 py-1.5 md:p-3 flex items-center justify-between bg-muted/50 gap-2 flex-shrink-0">
                      <h4 className="font-semibold text-xs md:text-sm truncate">{selectedDoc.name}</h4>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDownload(selectedDoc)}
                        className="flex-shrink-0 h-7 px-2 text-xs md:h-8 md:px-3 md:text-sm"
                      >
                        <Download className="w-3.5 h-3.5 md:w-4 md:h-4 mr-1" />
                        <span className="hidden sm:inline">Download</span>
                      </Button>
                    </div>
                    <div className="flex-1 overflow-y-auto p-2 md:p-4 min-h-0">
                      {isLoadingDoc ? (
                        <p className="text-xs text-muted-foreground">Loading...</p>
                      ) : (
                        <div className="prose prose-sm dark:prose-invert max-w-none text-xs md:text-sm overflow-x-auto break-words">
                          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
                            {docContent}
                          </ReactMarkdown>
                        </div>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="flex-1 flex items-center justify-center p-3">
                    <p className="text-xs text-muted-foreground">
                      {isLoadingList ? "Loading artifacts..." : "No artifacts available"}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Bottom: Chat Input + Approval (flex-shrink-0 stays at bottom) */}
            <div className="flex-shrink-0 flex flex-col gap-2 rounded-md border bg-muted/30 p-2 md:p-4">
              {/* Chat input */}
              <div className="flex gap-2 flex-shrink-0">
                <Textarea
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="Ask a question..."
                  disabled={isChatStreaming || isLoading}
                  rows={1}
                  className="flex-1 text-xs md:text-sm resize-none"
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

              {/* Approval gate */}
              <PhaseApprovalCard
                phaseName={phaseName}
                onApprove={onApprove}
                onRequestChanges={onRequestChanges}
                isLoading={isLoading || isChatStreaming}
              />
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
            className="flex flex-col min-h-0 min-w-0 w-full flex-1 gap-2"
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
