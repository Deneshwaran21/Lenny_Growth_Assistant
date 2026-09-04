const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export interface SourceCitation {
  transcript_id: string;
  episode_title: string;
  chunk_id: string;
  excerpt: string;
}

export interface SessionOut {
  id: string;
  user_id: string;
  title: string;
  provider: string;
  created_at: string;
  updated_at: string;
}

export interface MessageOut {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  provider_used: string | null;
  sources: SourceCitation[];
  skill_used: string | null;
  created_at: string;
}

export interface ChatResponse {
  session_id: string;
  message_id: string;
  reply: string;
  provider_used: string;
  skill_used: string;
  sources: SourceCitation[];
  artifact_id: string | null;
  grounded: boolean;
}

export interface ArtifactOut {
  id: string;
  session_id: string;
  kind: "markdown" | "html";
  title: string;
  content: string;
  sanitized: boolean;
  created_at: string;
}

export interface ProviderStatus {
  provider: string;
  configured: boolean;
  reachable: boolean | null;
  model: string | null;
}

export interface ConfigOut {
  active_provider: string;
  fallback_provider: string;
  providers: ProviderStatus[];
}

export interface HealthOut {
  status: "ok" | "degraded" | "down";
  database: boolean;
  knowledge_base_chunks: number;
  active_provider: string;
  detail: string | null;
}

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = body.detail || detail;
    } catch {
      // ignore parse errors, fall back to statusText
    }
    throw new ApiError(resp.status, detail);
  }
  return resp.json() as Promise<T>;
}

export const api = {
  health: () => request<HealthOut>("/api/health"),
  config: () => request<ConfigOut>("/api/config"),

  createSession: (userId: string, provider?: string) =>
    request<SessionOut>("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, provider }),
    }),
  listSessions: (userId: string) =>
    request<SessionOut[]>(`/api/sessions?user_id=${encodeURIComponent(userId)}`),
  getMessages: (sessionId: string) =>
    request<MessageOut[]>(`/api/sessions/${sessionId}/messages`),
  deleteSession: (sessionId: string) =>
    request<void>(`/api/sessions/${sessionId}`, { method: "DELETE" }),

  sendMessage: (
    sessionId: string,
    message: string,
    skill: "auto" | "qa" | "ship30" | "artifact",
    providerOverride?: string
  ) =>
    request<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        message,
        skill,
        provider_override: providerOverride || null,
      }),
    }),

  getArtifact: (artifactId: string) => request<ArtifactOut>(`/api/artifacts/${artifactId}`),
};

export { ApiError };