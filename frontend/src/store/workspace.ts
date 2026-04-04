import { create } from "zustand";
import { UIMessage, Job, JobStatus } from "@/types/api";

interface WorkspaceState {
  // Session
  sessionId: string;
  sessionTitle: string | null;
  setSessionTitle: (title: string) => void;

  // Messages
  messages: UIMessage[];
  addMessage: (msg: UIMessage) => void;
  appendToLastAssistantMessage: (chunk: string) => void;
  setLastAssistantJobId: (jobId: string) => void;
  finaliseAssistantMessage: () => void;

  // Streaming state
  isStreaming: boolean;
  setIsStreaming: (v: boolean) => void;

  // Jobs
  jobs: Record<string, Job>;
  upsertJob: (job: Job) => void;

  // Active viewer
  activeJobId: string | null;
  setActiveJobId: (id: string | null) => void;
  viewerMode: "model" | "preview" | "empty";
  setViewerMode: (mode: "model" | "preview" | "empty") => void;

  // Error toast
  toastError: string | null;
  setToastError: (msg: string | null) => void;
}

function generateSessionId(): string {
  // UUID v4 — works in all browsers
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// Persist sessionId in localStorage so page refreshes keep the session
function getOrCreateSessionId(): string {
  if (typeof window === "undefined") return generateSessionId();
  const stored = localStorage.getItem("claude3d_session_id");
  if (stored) return stored;
  const id = generateSessionId();
  localStorage.setItem("claude3d_session_id", id);
  return id;
}

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  sessionId: getOrCreateSessionId(),
  sessionTitle: null,
  setSessionTitle: (title) => set({ sessionTitle: title }),

  messages: [],
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),

  appendToLastAssistantMessage: (chunk) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant" && last.isStreaming) {
        msgs[msgs.length - 1] = { ...last, content: last.content + chunk };
      }
      return { messages: msgs };
    }),

  setLastAssistantJobId: (jobId) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, jobId };
      }
      return { messages: msgs };
    }),

  finaliseAssistantMessage: () =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, isStreaming: false };
      }
      return { messages: msgs };
    }),

  isStreaming: false,
  setIsStreaming: (v) => set({ isStreaming: v }),

  jobs: {},
  upsertJob: (job) =>
    set((s) => ({
      jobs: { ...s.jobs, [job.id]: job },
    })),

  activeJobId: null,
  setActiveJobId: (id) => set({ activeJobId: id }),
  viewerMode: "empty",
  setViewerMode: (mode) => set({ viewerMode: mode }),

  toastError: null,
  setToastError: (msg) => set({ toastError: msg }),
}));
