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

// Local UI-only message type (pre-ID assignment during streaming)
export interface UIMessage {
  id: string;          // temp or db id as string
  role: MessageRole;
  content: string;
  isStreaming?: boolean;
  jobId?: string;
}
