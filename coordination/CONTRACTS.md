# NOVA API Contracts — v1 (FROZEN 2026-11-07)

Authoritative types: `frontend/src/api/types.ts` (TS) ⇄ `backend/app/schemas.py` (Pydantic). Field names are identical.
Changes require a blocking proposal in `SCRATCHPAD.md` + an ADR in `DECISIONS.md` before code changes.

Base URL: `http://localhost:8000` (Vite dev server proxies `/api` → 8000). Default `student_id=demo_student`.

| Method | Route | Request | Response |
|---|---|---|---|
| GET | `/api/health` | – | `HealthResponse` |
| GET | `/api/dashboard?student_id=` | – | `DashboardResponse` |
| GET | `/api/connectors` | – | `ConnectorStatus[]` |
| POST | `/api/connectors/{provider}/sync?student_id=` | – | `SyncResponse` (provider ∈ canvas, google_calendar, gmail, piazza) |
| POST | `/api/connectors/sync?student_id=` | – | `SyncResponse[]` (all providers; failures isolated) |
| POST | `/api/documents/upload` | multipart `file`, optional `course_id`, `student_id` | `DocumentSummary` |
| POST | `/api/documents/demo/{name}?student_id=` | name ∈ `graded_quiz`, `ungraded_sheet` | `DocumentSummary` (labeled fixture PDF) |
| GET | `/api/documents?student_id=` | – | `DocumentSummary[]` |
| GET | `/api/documents/{id}/file` | – | `application/pdf` |
| POST | `/api/memory/ingest` | `{student_id, source_records?: SourceRecord[], observations?: Observation[]}` | `{accepted:int, duplicates:int, pending_review:int, belief_updates: BeliefUpdate[]}` |
| GET | `/api/memory/context?student_id=&query=&agent=` | – | `{narrative, facts: string[], relevant_beliefs: Belief[], source_records: SourceRecord[], evidence_refs: EvidenceRef[], uncertainties: string[], state_version:int}` |
| GET | `/api/memory/model?student_id=` | – | `StudentModel` (extension, see ADR-004) |
| GET | `/api/memory/graph?student_id=` | – | `GraphResponse` |
| GET | `/api/memory/history?student_id=` | – | `HistoryResponse` |
| POST | `/api/memory/self_confidence` | `{student_id, concept_id, value: 0..1}` | `{belief_updates: BeliefUpdate[]}` (self-report only; never changes mastery) |
| POST | `/api/memory/propositions/{id}` | `{student_id, status: "confirmed"|"disputed"}` | `SemanticProposition` |
| POST | `/api/chat` | `ChatRequest` | `ChatResponse` |
| GET | `/api/recommendations?student_id=&status=` | – | `Recommendation[]` |
| POST | `/api/recommendations/{id}/approve` | `ApproveRequest` | `ApproveResponse` (409 if not pending or confirm mismatch) |
| POST | `/api/recommendations/{id}/reject` | `{student_id}` | `{recommendation: Recommendation}` |
| GET | `/api/settings/privacy` | – | `PrivacySettings` (v1.1) |
| POST | `/api/settings/privacy` | `{mode: "off"|"local"|"cloud"}` | `PrivacySettings` (v1.1) |
| POST | `/api/demo/reset` | – | `{ok: true}` re-seeds fixtures (no quiz ingested) |

Errors: `{"detail": "..."}` with 4xx/5xx.
Timestamps: ISO 8601 with offset. Display in `student.timezone`.

## v1.1 (2026-11-07) — additive
- `ChatResponse.llm_provider: string|null`, `ChatResponse.llm_note: string|null`
- `HealthResponse.llm.mode: "off"|"local"|"cloud"`
- New `PrivacySettings` type + `/api/settings/privacy` routes (ADR-009)

## v1.2 (2026-11-07) — start empty, add data manually (ADR-010)
- `ConnectorState` += `"imported"`; `ConnectorStatus.mode` += `"import"` (items added from files, not live)
- `Insight.kind` += `"goal"`
- `DashboardResponse.knowledge: KnowledgeCounts`
- `StudentModel.proposition_evidence: Record<propId, EvidenceRef[]>`
- New types `ImportResult`, `DemoAsset`, `ImportKind`
- Routes:
  - `GET /api/imports/demo?student_id=` → `DemoAsset[]` (ordered, with `added`)
  - `POST /api/imports/demo/{name}?student_id=` → `ImportResult`
  - `POST /api/imports/upload` multipart `file`, `student_id`, `authored_by_me` ("true"/"false"), optional `course_id` → `ImportResult`
    (accepts .pdf, .eml, .ics, .md packs; 400 with `detail` on unsupported/invalid files)
  - `GET /api/imports?student_id=` → `ImportResult[]` newest first
- `POST /api/demo/reset` now resets to an EMPTY state (no courses, no data). LLM mode is preserved.
