"use client";
import { useCallback } from "react";
import { api } from "@/lib/api";
import { readSSEStream } from "@/lib/streaming";
import { useWorkspaceStore } from "@/store/workspace";

export function useChat() {
  const {
    sessionId,
    selectedProvider,
    selectedModel,
    isStreaming,
    setIsStreaming,
    addMessage,
    appendToLastAssistantMessage,
    setLastAssistantJobId,
    finaliseAssistantMessage,
    upsertJob,
    setActiveJobId,
    setViewerMode,
    setToastError,
  } = useWorkspaceStore();

  const sendMessage = useCallback(
    async (text: string) => {
      if (isStreaming || !text.trim()) return;

      // Optimistically add user message
      addMessage({ id: `user-${Date.now()}`, role: "user", content: text });

      // Add empty streaming assistant bubble
      addMessage({ id: `asst-${Date.now()}`, role: "assistant", content: "", isStreaming: true });

      setIsStreaming(true);

      try {
        const response = await api.chatStream(sessionId, text, selectedProvider, selectedModel ?? undefined);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        for await (const event of readSSEStream(response)) {
          switch (event.event) {
            case "delta":
              appendToLastAssistantMessage(event.data);
              break;

            case "job_created": {
              let jobId: string | null = null;
              try {
                const parsed = JSON.parse(event.data);
                jobId = parsed.job_id;
              } catch {}
              if (jobId) {
                setLastAssistantJobId(jobId);
                // Seed job as pending
                upsertJob({
                  id: jobId,
                  session_id: sessionId,
                  status: "pending",
                  phase: null,
                  error_message: null,
                  execution_time_ms: null,
                  has_stl: false,
                  has_preview: false,
                  has_step: false,
                  created_at: new Date().toISOString(),
                  started_at: null,
                  finished_at: null,
                });
                setActiveJobId(jobId);
                setViewerMode("empty");
              }
              break;
            }

            case "error":
            case "sandbox_error":
              setToastError(event.data || "An error occurred");
              break;

            case "done":
              finaliseAssistantMessage();
              break;
          }
        }
      } catch (err) {
        setToastError(err instanceof Error ? err.message : "Connection error");
        finaliseAssistantMessage();
      } finally {
        setIsStreaming(false);
      }
    },
    [
      sessionId, selectedProvider, selectedModel, isStreaming,
      addMessage, appendToLastAssistantMessage, setLastAssistantJobId,
      finaliseAssistantMessage, setIsStreaming, upsertJob,
      setActiveJobId, setViewerMode, setToastError,
    ]
  );

  return { sendMessage, isStreaming };
}
