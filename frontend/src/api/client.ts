import type {
  ApproveRequest,
  ApproveResponse,
  BeliefUpdate,
  Belief,
  ChatRequest,
  ChatResponse,
  ConnectorStatus,
  DashboardResponse,
  DocumentSummary,
  EvidenceRef,
  GraphResponse,
  HealthResponse,
  HistoryResponse,
  Observation,
  Provider,
  Recommendation,
  SemanticProposition,
  SourceRecord,
  StudentModel,
  SyncResponse,
} from "./types";

export const DEFAULT_STUDENT = "demo_student";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, init);
  } catch {
    throw new ApiError(0, "Backend unreachable — is the API running on :8000?");
  }
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    let parsed = false;
    try {
      const body = await res.json();
      parsed = true;
      if (body && typeof body.detail === "string") detail = body.detail;
      else if (body && body.detail) detail = JSON.stringify(body.detail);
    } catch {
      /* non-JSON body */
    }
    // The Vite dev proxy answers 5xx with a non-JSON body when the API is not running.
    if (!parsed && res.status >= 500) throw new ApiError(0, "Backend unreachable — is the API running on :8000?");
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

const q = (params: Record<string, string | undefined>) => {
  const s = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined) s.set(k, v);
  return s.toString();
};

const postJson = <T>(path: string, body: unknown) =>
  request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export interface IngestResponse {
  accepted: number;
  duplicates: number;
  pending_review: number;
  belief_updates: BeliefUpdate[];
}

export interface ContextResponse {
  narrative: string;
  facts: string[];
  relevant_beliefs: Belief[];
  source_records: SourceRecord[];
  evidence_refs: EvidenceRef[];
  uncertainties: string[];
  state_version: number;
}

export const api = {
  health: () => request<HealthResponse>("/api/health"),
  dashboard: (student_id = DEFAULT_STUDENT) =>
    request<DashboardResponse>(`/api/dashboard?${q({ student_id })}`),
  connectors: () => request<ConnectorStatus[]>("/api/connectors"),
  syncProvider: (provider: Provider, student_id = DEFAULT_STUDENT) =>
    request<SyncResponse>(`/api/connectors/${provider}/sync?${q({ student_id })}`, { method: "POST" }),
  syncAll: (student_id = DEFAULT_STUDENT) =>
    request<SyncResponse[]>(`/api/connectors/sync?${q({ student_id })}`, { method: "POST" }),
  uploadDocument: (file: File, course_id?: string, student_id = DEFAULT_STUDENT) => {
    const fd = new FormData();
    fd.append("file", file);
    if (course_id) fd.append("course_id", course_id);
    fd.append("student_id", student_id);
    return request<DocumentSummary>("/api/documents/upload", { method: "POST", body: fd });
  },
  loadDemoDocument: (name: "graded_quiz" | "ungraded_sheet", student_id = DEFAULT_STUDENT) =>
    request<DocumentSummary>(`/api/documents/demo/${name}?${q({ student_id })}`, { method: "POST" }),
  documents: (student_id = DEFAULT_STUDENT) =>
    request<DocumentSummary[]>(`/api/documents?${q({ student_id })}`),
  ingest: (body: { student_id: string; source_records?: SourceRecord[]; observations?: Observation[] }) =>
    postJson<IngestResponse>("/api/memory/ingest", body),
  context: (query: string, agent?: string, student_id = DEFAULT_STUDENT) =>
    request<ContextResponse>(`/api/memory/context?${q({ student_id, query, agent })}`),
  model: (student_id = DEFAULT_STUDENT) => request<StudentModel>(`/api/memory/model?${q({ student_id })}`),
  graph: (student_id = DEFAULT_STUDENT) => request<GraphResponse>(`/api/memory/graph?${q({ student_id })}`),
  history: (student_id = DEFAULT_STUDENT) => request<HistoryResponse>(`/api/memory/history?${q({ student_id })}`),
  setSelfConfidence: (concept_id: string, value: number, student_id = DEFAULT_STUDENT) =>
    postJson<{ belief_updates: BeliefUpdate[] }>("/api/memory/self_confidence", { student_id, concept_id, value }),
  setPropositionStatus: (id: string, status: "confirmed" | "disputed", student_id = DEFAULT_STUDENT) =>
    postJson<SemanticProposition>(`/api/memory/propositions/${encodeURIComponent(id)}`, { student_id, status }),
  chat: (body: ChatRequest) => postJson<ChatResponse>("/api/chat", body),
  recommendations: (status?: string, student_id = DEFAULT_STUDENT) =>
    request<Recommendation[]>(`/api/recommendations?${q({ student_id, status })}`),
  approve: (id: string, body: ApproveRequest) =>
    postJson<ApproveResponse>(`/api/recommendations/${encodeURIComponent(id)}/approve`, body),
  reject: (id: string, student_id = DEFAULT_STUDENT) =>
    postJson<{ recommendation: Recommendation }>(`/api/recommendations/${encodeURIComponent(id)}/reject`, { student_id }),
  resetDemo: () => request<{ ok: boolean }>("/api/demo/reset", { method: "POST" }),
};
