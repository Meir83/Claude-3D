import { Job, Session, ProvidersMap } from "@/types/api";

const BASE = "/api/v1";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  /** Start a streaming chat request. Returns the raw Response for SSE parsing. */
  chatStream(
    sessionId: string,
    message: string,
    provider: string = "claude",
    model?: string,
  ): Promise<Response> {
    return fetch(`${BASE}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message, provider, model }),
    });
  },

  getSession(sessionId: string): Promise<Session> {
    return apiFetch<Session>(`/chat/${sessionId}`);
  },

  getJob(jobId: string): Promise<Job> {
    return apiFetch<Job>(`/jobs/${jobId}`);
  },

  getJobs(sessionId: string, limit = 20, offset = 0): Promise<{ items: Job[]; total: number }> {
    return apiFetch(`/jobs?session_id=${sessionId}&limit=${limit}&offset=${offset}`);
  },

  jobEventsUrl(jobId: string): string {
    return `${BASE}/jobs/${jobId}/events`;
  },

  stlUrl(jobId: string): string {
    return `${BASE}/files/${jobId}/stl`;
  },

  previewUrl(jobId: string): string {
    return `${BASE}/files/${jobId}/preview`;
  },

  stepUrl(jobId: string): string {
    return `${BASE}/files/${jobId}/step`;
  },

  getProviders(): Promise<ProvidersMap> {
    return apiFetch<ProvidersMap>("/providers");
  },

  healthCheck(): Promise<{ status: string }> {
    return apiFetch("/health");
  },
};
