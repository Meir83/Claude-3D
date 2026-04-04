export type MessageRole = "user" | "assistant";

export interface Message {
  id: number;
  session_id: string;
  role: MessageRole;
  content: string;
  created_at: string;
}

export type JobStatus = "pending" | "running" | "done" | "error";

export interface Job {
  id: string;
  session_id: string;
  status: JobStatus;
  phase: number | null;
  error_message: string | null;
  execution_time_ms: number | null;
  has_stl: boolean;
  has_preview: boolean;
  has_step: boolean;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface Session {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  messages: Message[];
}

export interface ChatStreamEvent {
  event: "delta" | "code_extracted" | "job_created" | "done" | "error" | "sandbox_error" | "heartbeat";
  data: string;
}

// ── Providers ─────────────────────────────────────────────────────────────────

export type ProviderId = "claude" | "gemini" | "ollama";

export interface ProviderModel {
  id: string;
  name: string;
  default?: boolean;
}

export interface Provider {
  name: string;
  models: ProviderModel[];
  requires_key: boolean;
  key_env: string | null;
  free: boolean;
  available: boolean;
  default_model: string;
}

export type ProvidersMap = Record<ProviderId, Provider>;

// ── Local UI-only message type ─────────────────────────────────────────────────

export interface UIMessage {
  id: string;          // temp or db id as string
  role: MessageRole;
  content: string;
  isStreaming?: boolean;
  jobId?: string;
}
