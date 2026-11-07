// FROZEN CONTRACT v1 — mirrors backend/app/schemas.py. See coordination/CONTRACTS.md.
// Change only via a logged proposal in coordination/SCRATCHPAD.md + DECISIONS.md.

export type Provider = "canvas" | "google_calendar" | "gmail" | "piazza" | "documents";

export type ConnectorState = "connected" | "needs_auth" | "failed" | "demo_data" | "not_available";

export interface ConnectorStatus {
  provider: Provider;
  state: ConnectorState;
  mode: "live" | "fixture" | "none";
  detail: string;
  last_synced_at: string | null;
  record_count: number;
  verified_live: boolean; // true only after a successful live API call this process
}

export interface SourceRecord {
  id: string;
  student_id: string;
  provider: Provider;
  external_id: string;
  kind: string; // assignment | calendar_event | message | discussion | event_announcement | document | assessment | self_report
  title: string;
  body: string;
  source_url: string | null;
  occurred_at: string | null; // due date for assignments, start for events, sent date for mail
  fetched_at: string;
  course_id: string | null;
  concept_ids: string[];
  metadata: Record<string, unknown>;
  is_fixture: boolean;
}

export interface EvidenceRef {
  id: string; // observation id or source record id
  label: string; // e.g. "Systems Quiz 3, p. 2, Q3"
  provider: string;
  source_record_id: string | null;
  page: number | null;
  question_id: string | null;
  url: string | null; // e.g. /api/documents/doc_x/file#page=2
  is_fixture: boolean;
}

export interface Observation {
  event_id: string;
  student_id: string;
  source_record_id: string | null;
  source: string; // pdf_assessment | chat | self_report | connector | fixture
  event_type: string; // assessment_answer | self_confidence | goal | preference | interest | mood | study_session_completed
  course_id: string | null;
  concept_id: string | null;
  occurred_at: string;
  payload: Record<string, unknown>;
  extraction_confidence: number;
  status: "accepted" | "pending_review" | "rejected";
  is_fixture: boolean;
}

export interface Belief {
  id: string;
  student_id: string;
  scope: { level: "global" | "course" | "concept"; course_id?: string | null; concept_id?: string | null };
  key: string; // knowledge.mastery | knowledge.self_confidence | workload.upcoming_due | motivation.self_report | engagement.sessions_completed
  value: number | string | null;
  evidence_strength: "none" | "weak" | "moderate" | "strong";
  status: "estimated" | "self_reported" | "source_fact" | "expired";
  evidence_ids: string[];
  updated_at: string;
  expires_at: string | null;
  version: number;
}

export interface SemanticProposition {
  id: string;
  student_id: string;
  statement: string;
  category: "goal" | "interest" | "preference" | "other";
  scope: string; // "global" | course id
  status: "self_reported" | "inferred" | "confirmed" | "disputed" | "expired";
  evidence_ids: string[];
  updated_at: string;
}

export interface GraphNode {
  id: string; // "course:systems" | "concept:cache_coherence" | "goal:prop_x" | "evidence:obs_x"
  type: "course" | "concept" | "goal" | "evidence";
  label: string;
  data: Record<string, unknown>; // concept: {mastery, self_confidence, evidence_count, blind_spot}
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: "contains" | "prerequisite_of" | "assessed_by" | "supports_goal" | "related_to";
  provenance: "fixture" | "verified" | "evidence";
}

export interface ConceptState {
  concept_id: string;
  course_id: string;
  label: string;
  mastery: number | null; // BKT estimate; null when no accepted assessment evidence
  evidence_strength: "none" | "weak" | "moderate" | "strong";
  correct: number;
  incorrect: number;
  self_confidence: number | null; // separate self-report, never mixed with mastery
  blind_spot: boolean; // candidate signal only
  stale: boolean;
  last_evidence_at: string | null;
  evidence: EvidenceRef[];
}

export interface StudentModel {
  student: { id: string; name: string; timezone: string };
  concepts: ConceptState[];
  courses: { course_id: string; label: string; upcoming_due: number; is_fixture: boolean }[];
  propositions: SemanticProposition[];
  global_beliefs: Belief[];
  narrative: string;
  state_version: number;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  beliefs: Belief[];
}

export interface BeliefUpdate {
  belief_id: string;
  key: string;
  scope: Belief["scope"];
  old_value: number | string | null;
  new_value: number | string | null;
  version: number;
  evidence_ids: string[];
  at: string;
}

export interface HistoryResponse {
  observations: Observation[];
  belief_updates: BeliefUpdate[];
}

export interface Factor {
  name: string; // goal_relevance | concept_gap | deadline_urgency | feasible_time | interest_match
  value: number; // 0..1
  explanation: string;
}

export interface Recommendation {
  id: string;
  student_id: string;
  type: "study_session" | "attend_event" | "review_opportunity";
  title: string;
  reason: string;
  evidence_ids: string[];
  evidence: EvidenceRef[];
  factors: Factor[];
  suggested_start: string | null;
  duration_minutes: number | null;
  status: "pending" | "approved" | "rejected" | "executed" | "executed_simulated" | "failed";
  proposed_action: { provider: string; operation: string; args: Record<string, unknown> } | null;
  result_detail: string | null;
  created_at: string;
  is_fixture: boolean;
}

export interface Opportunity {
  record: SourceRecord;
  relevance_score: number; // 0..1 heuristic
  relevance_reasons: string[];
  event_start: string | null; // null => never shown as "upcoming at"
  timing_label: string; // "Tue Nov 10, 4:00 PM EST" or "Worth reviewing — no event date found"
  speaker: string | null;
  venue: string | null;
  url: string | null;
  recommendation_id: string | null;
}

export interface FreeWindow {
  start: string;
  end: string;
  minutes: number;
}

export interface DocumentQuestion {
  question_id: string;
  page: number;
  concept_id: string | null;
  topic_text: string | null;
  correct: boolean | null;
  evidence_text: string;
  status: "accepted" | "pending_review" | "no_grade";
  observation_id: string | null;
}

export interface DocumentSummary {
  id: string;
  filename: string;
  title: string;
  course_id: string | null;
  page_count: number;
  status: "parsed" | "failed";
  kind: "graded_assessment" | "study_material";
  observations_created: number;
  pending_review: number;
  questions: DocumentQuestion[];
  uploaded_at: string;
  is_fixture: boolean;
  source_record_id: string;
  error: string | null;
  file_url: string; // /api/documents/{id}/file
}

export interface SourceCard {
  provider: Provider;
  label: string;
  status: ConnectorStatus;
  items: SourceRecord[];
}

export interface Insight {
  id: string;
  kind: "focus_area" | "blind_spot" | "deadline" | "stale_evidence" | "opportunity" | "missing_evidence";
  title: string;
  detail: string;
  course_id: string | null;
  concept_id: string | null;
  evidence: EvidenceRef[];
  confidence_note: string;
}

export interface DashboardResponse {
  student: { id: string; name: string; timezone: string };
  generated_at: string;
  demo_mode: boolean;
  cards: {
    canvas: SourceCard;
    google_calendar: SourceCard & { free_windows: FreeWindow[] };
    gmail: SourceCard & { opportunities: Opportunity[] };
    piazza: SourceCard;
    documents: { provider: "documents"; label: string; status: ConnectorStatus; documents: DocumentSummary[] };
  };
  insights: Insight[];
  recommendations: Recommendation[]; // pending only
  connectors: ConnectorStatus[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  message: string;
  student_id: string;
  history?: ChatMessage[];
}

export interface ChatResponse {
  answer: string; // markdown-lite: paragraphs + "- " bullets + **bold**
  intent: "struggling" | "weekly_focus" | "course_next" | "opportunities" | "sources" | "memory_update" | "general";
  sources: EvidenceRef[];
  beliefs_used: string[];
  uncertainties: string[];
  proposed_recommendations: Recommendation[];
  memory_updates: string[]; // human-readable descriptions of beliefs/propositions changed by this message
  llm_used: boolean;
  trace: string[]; // LangGraph node path
}

export interface SyncResponse {
  provider: Provider;
  status: ConnectorStatus;
  records_added: number;
  records_total: number;
  errors: string[];
}

export interface ApproveRequest {
  student_id: string;
  // Exact values the student reviewed; server rejects if they differ from the stored proposal.
  confirm: { title: string; suggested_start: string | null; duration_minutes: number | null };
}

export interface ApproveResponse {
  recommendation: Recommendation;
  executed: boolean;
  simulated: boolean;
  result_detail: string;
}

export interface HealthResponse {
  status: "ok";
  db: "ok" | "error";
  demo_mode: boolean;
  llm: { enabled: boolean; model: string | null };
  providers: ConnectorStatus[];
}
