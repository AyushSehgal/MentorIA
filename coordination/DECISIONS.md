# Architecture Decision Records

## ADR-001 Stack
Status: accepted. FastAPI + Pydantic v2 + SQLite (stdlib sqlite3, JSON columns) + LangGraph 1.x; React 18 + TS + Vite, no UI kit.
Rationale: minimal deps, local demo. Consequence: single process backend on :8000, Vite on :5173 with /api proxy.

## ADR-002 Agent split
Status: accepted. Coordinator owns all backend + contracts; one frontend agent owns `frontend/**` except `src/api/types.ts`.
Rationale: backend modules are tightly coupled (memory ↔ planning ↔ chat); the frontend is the cleanly separable scope.

## ADR-003 Deterministic grounding first, LLM optional
Status: superseded by ADR-009 (principle unchanged). LangGraph nodes compute grounded answers from stored evidence with templates. If `LLM_ENABLED=true`, Claude (`claude-opus-5-5`) may rephrase the draft but is instructed not to add facts; any failure → deterministic draft. `llm_used` is reported in every ChatResponse.

## ADR-004 `/api/memory/model` extension
Status: accepted. Added a typed StudentModel summary route so the UI does not reconstruct concept state from raw beliefs.

## ADR-005 BKT replay
Status: accepted. Mastery for a concept is recomputed by replaying all accepted assessment observations chronologically from prior p0=0.3 (s=0.1, g=0.2, T=0.1; illustrative, uncalibrated). Guarantees idempotency and order-independence of ingestion. No mastery belief exists without accepted assessment evidence.

## ADR-006 Fixture dates are relative
Status: accepted. Fixture timestamps are offsets from "today" in the student timezone so the demo stays coherent on any day. All fixture records carry `is_fixture=true` and UI shows "Demo data".

## ADR-007 Interpreting signals
Status: accepted. Blind-spot candidate = self_confidence − mastery ≥ 0.3 AND ≥2 accepted assessment answers. Evidence older than 60 days is flagged stale. Mood self-reports expire after 24h. Student questions (Piazza/chat) never lower mastery.

## ADR-008 Single markdown file for synthetic data
Status: accepted (supersedes the JSON fixtures of ADR-006; relative times kept).
Decision: `fixtures/synthetic_world.md` is the only source of synthetic data — courses, concepts, relations, student profile,
self-reports, and Canvas/Calendar/Gmail/Piazza records. Parsed by `backend/app/synthetic.py`, re-read on file change.
Connectors fall back to it per provider when not configured. Invalid edits keep the last valid version and surface the error
in connector status. Self-report rows are ingested on Sync all (idempotent by id).
Rationale: one human-editable file for the demo; real connectors can replace providers one at a time.

## ADR-009 User-selected LLM privacy modes (off / local / cloud)
Status: accepted. Supersedes the Anthropic-only phrasing layer of ADR-003; deterministic grounding is still authoritative.
Decision: modes are local (DEFAULT: an OpenAI-compatible server whose URL must be localhost; Ollama by default), off, and cloud
(OpenRouter by default, with `provider.data_collection="deny"`; Anthropic direct optional). The mode is chosen in the UI and
persisted in the DB (it survives demo resets). Only the question and grounded draft are sent. Rewrites that add numbers or
drop Q-citations or bold items are discarded. OpenAI-compatible calls use raw HTTP (`requests`), with no extra SDK.
Rationale: students decide where their data goes; local works offline; a small model can't silently change facts.
Amendment (2026-11-07, user request): default changed from off to local. If no local server is up, answers fall back to the
grounded draft after a ~1.5 s probe.
Consequences: the local path adds 5–25 s latency per answer; the guard can reject a rewrite, so the draft is shown instead.
