"""FROZEN CONTRACT v1 — mirrors frontend/src/api/types.ts. See coordination/CONTRACTS.md."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Provider = Literal["canvas", "google_calendar", "gmail", "piazza", "documents"]
ConnectorState = Literal["connected", "needs_auth", "failed", "demo_data", "not_available"]
Strength = Literal["none", "weak", "moderate", "strong"]


class ConnectorStatus(BaseModel):
    provider: Provider
    state: ConnectorState
    mode: Literal["live", "fixture", "none"]
    detail: str
    last_synced_at: Optional[str] = None
    record_count: int = 0
    verified_live: bool = False


class SourceRecord(BaseModel):
    id: str
    student_id: str
    provider: Provider
    external_id: str
    kind: str
    title: str
    body: str = ""
    source_url: Optional[str] = None
    occurred_at: Optional[str] = None
    fetched_at: str
    course_id: Optional[str] = None
    concept_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_fixture: bool = False


class EvidenceRef(BaseModel):
    id: str
    label: str
    provider: str
    source_record_id: Optional[str] = None
    page: Optional[int] = None
    question_id: Optional[str] = None
    url: Optional[str] = None
    is_fixture: bool = False


class Observation(BaseModel):
    event_id: str
    student_id: str
    source_record_id: Optional[str] = None
    source: str
    event_type: str
    course_id: Optional[str] = None
    concept_id: Optional[str] = None
    occurred_at: str
    payload: dict[str, Any] = Field(default_factory=dict)
    extraction_confidence: float = 1.0
    status: Literal["accepted", "pending_review", "rejected"] = "accepted"
    is_fixture: bool = False


class BeliefScope(BaseModel):
    level: Literal["global", "course", "concept"]
    course_id: Optional[str] = None
    concept_id: Optional[str] = None


class Belief(BaseModel):
    id: str
    student_id: str
    scope: BeliefScope
    key: str
    value: Optional[float | str] = None
    evidence_strength: Strength = "none"
    status: Literal["estimated", "self_reported", "source_fact", "expired"]
    evidence_ids: list[str] = Field(default_factory=list)
    updated_at: str
    expires_at: Optional[str] = None
    version: int = 1


class SemanticProposition(BaseModel):
    id: str
    student_id: str
    statement: str
    category: Literal["goal", "interest", "preference", "other"] = "other"
    scope: str = "global"
    status: Literal["self_reported", "inferred", "confirmed", "disputed", "expired"] = "self_reported"
    evidence_ids: list[str] = Field(default_factory=list)
    updated_at: str


class GraphNode(BaseModel):
    id: str
    type: Literal["course", "concept", "goal", "evidence"]
    label: str
    data: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: Literal["contains", "prerequisite_of", "assessed_by", "supports_goal", "related_to"]
    provenance: Literal["fixture", "verified", "evidence"]


class ConceptState(BaseModel):
    concept_id: str
    course_id: str
    label: str
    mastery: Optional[float] = None
    evidence_strength: Strength = "none"
    correct: int = 0
    incorrect: int = 0
    self_confidence: Optional[float] = None
    blind_spot: bool = False
    stale: bool = False
    last_evidence_at: Optional[str] = None
    evidence: list[EvidenceRef] = Field(default_factory=list)


class StudentInfo(BaseModel):
    id: str
    name: str
    timezone: str


class CourseSummary(BaseModel):
    course_id: str
    label: str
    upcoming_due: int
    is_fixture: bool


class StudentModel(BaseModel):
    student: StudentInfo
    concepts: list[ConceptState]
    courses: list[CourseSummary]
    propositions: list[SemanticProposition]
    global_beliefs: list[Belief]
    narrative: str
    state_version: int


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    beliefs: list[Belief]


class BeliefUpdate(BaseModel):
    belief_id: str
    key: str
    scope: BeliefScope
    old_value: Optional[float | str] = None
    new_value: Optional[float | str] = None
    version: int
    evidence_ids: list[str] = Field(default_factory=list)
    at: str


class HistoryResponse(BaseModel):
    observations: list[Observation]
    belief_updates: list[BeliefUpdate]


class Factor(BaseModel):
    name: str
    value: float
    explanation: str


class ProposedAction(BaseModel):
    provider: str
    operation: str
    args: dict[str, Any] = Field(default_factory=dict)


class Recommendation(BaseModel):
    id: str
    student_id: str
    type: Literal["study_session", "attend_event", "review_opportunity"]
    title: str
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    factors: list[Factor] = Field(default_factory=list)
    suggested_start: Optional[str] = None
    duration_minutes: Optional[int] = None
    status: Literal["pending", "approved", "rejected", "executed", "executed_simulated", "failed"] = "pending"
    proposed_action: Optional[ProposedAction] = None
    result_detail: Optional[str] = None
    created_at: str
    is_fixture: bool = False


class Opportunity(BaseModel):
    record: SourceRecord
    relevance_score: float
    relevance_reasons: list[str]
    event_start: Optional[str] = None
    timing_label: str
    speaker: Optional[str] = None
    venue: Optional[str] = None
    url: Optional[str] = None
    recommendation_id: Optional[str] = None


class FreeWindow(BaseModel):
    start: str
    end: str
    minutes: int


class DocumentQuestion(BaseModel):
    question_id: str
    page: int
    concept_id: Optional[str] = None
    topic_text: Optional[str] = None
    correct: Optional[bool] = None
    evidence_text: str
    status: Literal["accepted", "pending_review", "no_grade"]
    observation_id: Optional[str] = None


class DocumentSummary(BaseModel):
    id: str
    filename: str
    title: str
    course_id: Optional[str] = None
    page_count: int
    status: Literal["parsed", "failed"]
    kind: Literal["graded_assessment", "study_material"]
    observations_created: int = 0
    pending_review: int = 0
    questions: list[DocumentQuestion] = Field(default_factory=list)
    uploaded_at: str
    is_fixture: bool = False
    source_record_id: str
    error: Optional[str] = None
    file_url: str


class SourceCard(BaseModel):
    provider: Provider
    label: str
    status: ConnectorStatus
    items: list[SourceRecord]


class CalendarCard(SourceCard):
    free_windows: list[FreeWindow]


class GmailCard(SourceCard):
    opportunities: list[Opportunity]


class DocumentsCard(BaseModel):
    provider: Literal["documents"] = "documents"
    label: str
    status: ConnectorStatus
    documents: list[DocumentSummary]


class Insight(BaseModel):
    id: str
    kind: Literal["focus_area", "blind_spot", "deadline", "stale_evidence", "opportunity", "missing_evidence"]
    title: str
    detail: str
    course_id: Optional[str] = None
    concept_id: Optional[str] = None
    evidence: list[EvidenceRef] = Field(default_factory=list)
    confidence_note: str = ""


class DashboardCards(BaseModel):
    canvas: SourceCard
    google_calendar: CalendarCard
    gmail: GmailCard
    piazza: SourceCard
    documents: DocumentsCard


class DashboardResponse(BaseModel):
    student: StudentInfo
    generated_at: str
    demo_mode: bool
    cards: DashboardCards
    insights: list[Insight]
    recommendations: list[Recommendation]
    connectors: list[ConnectorStatus]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    student_id: str = "demo_student"
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    intent: Literal["struggling", "weekly_focus", "course_next", "opportunities", "sources", "memory_update", "general"]
    sources: list[EvidenceRef] = Field(default_factory=list)
    beliefs_used: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    proposed_recommendations: list[Recommendation] = Field(default_factory=list)
    memory_updates: list[str] = Field(default_factory=list)
    llm_used: bool = False
    llm_provider: Optional[str] = None  # e.g. "local:qwen2.5"; None when the deterministic draft was shown
    llm_note: Optional[str] = None  # why the LLM was skipped/discarded, if it was
    trace: list[str] = Field(default_factory=list)


class SyncResponse(BaseModel):
    provider: Provider
    status: ConnectorStatus
    records_added: int
    records_total: int
    errors: list[str] = Field(default_factory=list)


class ApproveConfirm(BaseModel):
    title: str
    suggested_start: Optional[str] = None
    duration_minutes: Optional[int] = None


class ApproveRequest(BaseModel):
    student_id: str = "demo_student"
    confirm: ApproveConfirm


class ApproveResponse(BaseModel):
    recommendation: Recommendation
    executed: bool
    simulated: bool
    result_detail: str


class RejectRequest(BaseModel):
    student_id: str = "demo_student"


class IngestRequest(BaseModel):
    student_id: str = "demo_student"
    source_records: list[SourceRecord] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)


class IngestResponse(BaseModel):
    accepted: int
    duplicates: int
    pending_review: int
    belief_updates: list[BeliefUpdate]


class ContextResponse(BaseModel):
    narrative: str
    facts: list[str]
    relevant_beliefs: list[Belief]
    source_records: list[SourceRecord]
    evidence_refs: list[EvidenceRef]
    uncertainties: list[str]
    state_version: int


class SelfConfidenceRequest(BaseModel):
    student_id: str = "demo_student"
    concept_id: str
    value: float = Field(ge=0, le=1)


class PropositionStatusRequest(BaseModel):
    student_id: str = "demo_student"
    status: Literal["confirmed", "disputed"]


class LLMInfo(BaseModel):
    enabled: bool
    model: Optional[str] = None
    mode: Literal["off", "local", "cloud"] = "off"


class PrivacySettings(BaseModel):
    mode: Literal["off", "local", "cloud"]
    local_available: bool
    local_detail: str
    cloud_available: bool
    cloud_detail: str
    data_leaves_device: bool
    sent_to_llm: str


class PrivacyUpdate(BaseModel):
    mode: Literal["off", "local", "cloud"]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    db: Literal["ok", "error"]
    demo_mode: bool
    llm: LLMInfo
    providers: list[ConnectorStatus]
