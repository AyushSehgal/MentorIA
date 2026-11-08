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

## ADR-010 Start empty; data enters through manual imports
Status: accepted (supersedes ADR-008's auto-loaded synthetic file).
Decision: MentorIA starts with an empty DB and catalog. Courses/concepts come from course-overview PDFs (`Course ID:` +
`Concept:` lines) or .md packs; graded PDFs become evidence; .eml/.ics/.md add source items; student-authored text
(ticked "I wrote this", emails sent from MENTORIA_STUDENT_EMAIL, chat) yields goals/interests/preferences. Similar
statements of the same category merge into one proposition with multiple evidence ids. Imported items survive live syncs.
14 demo assets for 10-601 and 16-831 are generated daily (`demo_assets/`, gitignored).
Rationale: the demo shows the model growing as context is added; one honest path for all data.

## ADR-011 Rename NOVA → MentorIA
Status: accepted. All text, env vars (MENTORIA_*), the demo marker and DB filename renamed. Old `backend/data/nova.db` is no longer read.

## ADR-012 "About me" chat mode
Status: accepted. Chat panel has Ask and About me tabs (ChatRequest.mode). In tell mode every message is saved: explicit
patterns first, else a keyword classifier picks goal/interest/preference/mood, else a general note. Tell replies skip the LLM.

## ADR-013 Prepopulated start, third course with shared concepts, no visible demo labels
Status: accepted (user request; partially reverses ADR-010's empty start; overrides spec invariant #9 for the UI only).
Decision: on first start and on reset, all sample files are imported (MENTORIA_PREPOPULATE, default true). The Add data
tab is hidden. 10-605 is added; its overview's `Shared concept:` lines add the course to existing concepts (`also_in`), so
shared topics keep one estimate with evidence from both courses. The UI never shows "demo"; `is_fixture` stays in the
API and assets carry a hidden marker (PDF metadata / email header / .ics property / .md comment).
Consequence: presenters must state that the data is fictional sample data.

## ADR-014 About me lives on the Student Model page and answers questions about the student
Status: accepted (user request; Dashboard owner approved). Amends ADR-012's "every message is saved".
Decision: the Dashboard chat is Ask only. The Student Model page has a side panel: a belief summary (goals, check this,
gaps, solid, preferences, feeling — all from stored beliefs) plus the About me chat. In tell mode a question about the
student is answered from the model (orchestration node `about_me`) and saves nothing; statements are saved as before.
The concept map defaults to a calm view (only topics with graded work or a confidence rating; relation and goal lines
only around the selection) with an "All topics" toggle.
Rationale: one place shows what the model believes and lets the student correct or extend it; questions must never
pollute the profile (e.g. "Am I confident in X?" would otherwise save a confidence of 0.8).
Consequence: tell-mode question detection is a heuristic; a statement phrased as a question is answered, not saved.

## ADR-015 Label sample data again, now that real accounts are connected
Status: accepted (user request, 2026-11-07). Amends ADR-013 ("the UI never shows demo labels").
Context: Canvas, Google Calendar, Gmail and Ed are now live, so real and fictional items sit side by side.
Decision: every item with `is_fixture: true` is marked "Sample" (tooltip: fictional sample data, not from your accounts):
assignment and discussion rows, all-sample course groups, calendar events (dashed outline + tag in the detail view),
evidence chips (chat, inspector, goals), sample courses in Details, and a one-line note on Student Model naming the sample
courses. Chat answers that cite sample data add the caveat "Some cited sources are sample data (fictional)"; forum summaries
mark sample posts inline. Real data stays unmarked.

## ADR-016 Cloud model chooses the answer type; keywords remain the fallback
Status: accepted (user request, 2026-11-07).
Decision: in cloud mode, `llm.classify_intent` sends only the question to the configured cloud model, which replies with one
label from a fixed list (the capability names). Anything else, a timeout (8 s) or any error falls back to the keyword router;
off and local modes never call it. Facts still come only from stored data; the model only chooses which grounded answer runs.
Keyword rules were also fixed: assignment/deadline words beat a bare "this week"; "focus/prioritize/what should I" still
means the study plan.
Rationale: keyword order sent "Assignments this week" to the study plan. Consequence: about +1-2 s per question in cloud mode.
