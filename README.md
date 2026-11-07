# NOVA — academic aggregation dashboard + student model

NOVA consolidates Canvas, Google Calendar, Gmail, Piazza and uploaded PDFs into one React dashboard, keeps a
persistent, evidence-backed student model (BKT mastery, separate self-confidence, goals/preferences, workload),
and answers cross-source questions through a LangGraph orchestrator. External writes (calendar events) happen only
after explicit student approval.

Spec: `NOVA_CLAUDE_IMPLEMENTATION.md` · Contracts: `coordination/CONTRACTS.md` · Decisions: `coordination/DECISIONS.md`

## Run it

Requirements: Python 3.12 + [uv](https://docs.astral.sh/uv/), Node 18+.

```bash
./scripts/dev.sh
```
Installs dependencies on first run, starts the API on http://localhost:8000 and the UI on **http://localhost:5173**.

Or start each process separately:
```bash
uv venv backend/.venv --python 3.12 && uv pip install --python backend/.venv/bin/python -r backend/requirements.txt
backend/.venv/bin/uvicorn app.main:app --app-dir backend --port 8000
npm --prefix frontend install && npm --prefix frontend run dev
```

Reset the demo (also available as a button on the Sources page): `backend/.venv/bin/python scripts/seed_demo.py` (add `--with-quiz` to pre-ingest the graded quiz).

Tests: `cd backend && .venv/bin/python -m pytest -q` · Frontend typecheck/build: `npm --prefix frontend run build`

## Demo script (3–4 min)
1. **Dashboard**: Canvas due-soon, Calendar + free windows, Gmail opportunities, Piazza, Documents — each card shows its connector state; fixtures say **Demo data**.
2. Ask chat **“What systems topics am I struggling with?”** → honest “no graded evidence yet”.
3. **Documents → Load demo graded quiz**: 7 questions with page refs; 6 accepted, Q7 (partial credit) held for review.
4. Ask again → Cache Coherence 0.12 (Q2 p.1, Q3 p.2 incorrect), blind-spot candidate (self-confidence 0.85), Synchronization 0.15; caveats listed.
5. **“What should I focus on this week?”** → priorities from gap × deadline × goal × free time; approval cards. Approve → labeled *Simulated* (Calendar write not configured); Reject → no side effect.
6. **“Any research talks I should attend?”** → robotics seminar matched to the embodied-AI goal with an approval-gated calendar proposal; the undated RA call shows “Worth reviewing — no event date found”.
7. **Student Model**: mastery vs. self-confidence, provenance chips, propositions (confirm/dispute), knowledge graph, belief-update history.
8. Optional: type “I'm interested in tactile sensing” or “I'm feeling unmotivated today” to show explicit memory updates (the latter expires in 24h).

## Integration status (truthful)

| Source | Status | Notes |
|---|---|---|
| Canvas | **MOCK_ONLY** | REST adapter implemented (`connectors/canvas.py`), not tested live: no credentials were available. Demo shows labeled fixtures. |
| Google Calendar read | **MOCK_ONLY** | Adapter + token refresh implemented, untested live. |
| Google Calendar write | **MOCK_ONLY** | Approved writes are *simulated* and labeled unless `GOOGLE_CALENDAR_WRITE_ENABLED=true` and the token has `calendar.events` scope. Idempotent via private extended property. Untested live. |
| Gmail | **MOCK_ONLY** | Read-only, query-filtered, bodies clipped. Untested live. |
| Piazza | **MOCK_ONLY** | No official API; optional unofficial `piazza-api` path behind `PIAZZA_ENABLED`. Untested. |
| PDF upload | **Working** | Tested with generated demo PDFs (graded + ungraded). Text-based PDFs only (no OCR). |
| LLM phrasing | **Off by default, untested** | `LLM_ENABLED=true` + `ANTHROPIC_API_KEY` lets Claude rephrase the deterministic grounded draft; any failure falls back to the deterministic draft. `llm_used` is reported per answer. |

To connect real services: copy `.env.example` to `.env`, fill in credentials, run `backend/.venv/bin/python scripts/google_auth.py` for Google, restart, and press **Sync all**. A card changes to `connected` / `verified_live: true` only after a successful live call. Failures show `failed` with the error plus labeled fixtures; other cards are unaffected.

## Architecture
- `backend/app/connectors/` adapters → `services/aggregation.py` (sync, dedup on `(provider, external_id)`, isolate failures).
- `services/document_ingest.py`: PDF → page text → per-question grading markers → `Observation`s (pending review when ambiguous).
- `memory/`: immutable observations, `updates.py` (the only writer of beliefs; BKT replay), `context.py` (student model, graph, narrative, `/api/memory/context`).
- `orchestration/graph.py`: LangGraph `route → memory_update? → {struggling | weekly_focus | course_next | opportunities | sources | general} → compose`.
- `services/planning.py`, `opportunity_ranking.py`, `actions.py` (approval validation + idempotent execution).
- `frontend/`: Vite + React + TS; pages Dashboard, Student Model, Documents, Sources; persistent chat panel.

## Known gaps
- No live connector verified (no credentials in this environment). BKT parameters are illustrative, uncalibrated.
- Concept map, courses and prerequisites are labeled fixtures; no course catalog (course recommendations say so).
- Intent routing is keyword-based; free-form questions outside the main intents get a context summary.
- No OCR for scanned PDFs; questions spanning a page break are not parsed.
- Single-user local demo: no auth on the API.
