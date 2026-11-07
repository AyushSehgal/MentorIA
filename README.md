# MentorIA — academic aggregation dashboard + student model

MentorIA consolidates Canvas, Google Calendar, Gmail, Piazza and uploaded PDFs into one React dashboard, keeps a
persistent, evidence-backed student model (BKT mastery, separate self-confidence, goals/preferences, workload),
and answers cross-source questions through a LangGraph orchestrator. External writes (calendar events) happen only
after explicit student approval.

Spec: `MentorIA_CLAUDE_IMPLEMENTATION.md` · Contracts: `coordination/CONTRACTS.md` · Decisions: `coordination/DECISIONS.md`

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

## Starting data (prepopulated)

MentorIA starts **prepopulated**: on first start (and on **Sources → Reset**) it imports the 16 sample files in
`demo_assets/` through the normal import pipeline, so the dashboard is full from the first load:

- **Three courses** with concepts from their public course pages: **10-601** Intro to ML, **16-831** Intro to Robot
  Learning, **10-605** ML with Large Datasets.
- **Overlap:** 10-605 shares 6 concepts with 10-601 (optimization/SGD, linear regression, backprop/autodiff, neural
  nets, transformers, matrix factorization). A shared concept is *one* concept with one estimate, so a missed
  autodiff question in 10-605 and two missed backprop questions in 10-601 form a single Backpropagation estimate.
- Assignments, a week of calendar, graded 10-601 Quiz 2 / 16-831 HW2 / 10-605 lecture quizzes, your career statement,
  an email to your advisor, inbox announcements and Piazza posts.

The student, grades, emails and events are **fictional sample data**. The UI doesn't label them (presenter's choice,
ADR-013); the API still flags them with `is_fixture: true`, and the files carry a hidden marker. Say so when presenting.
`MENTORIA_PREPOPULATE=false` gives an empty start; the import page still exists at `/documents` (not in the nav) and
accepts .pdf, .eml, .ics and .md files.

**About me** — the chat panel has two tabs: **Ask** (questions) and **About me** (everything you type is saved to your
profile: goals, interests, how you study, confidence, how you feel).

## Language models & privacy

**No LLM is required.** Every answer is assembled from stored evidence (quiz pages, deadlines, calendar, goals) by the
LangGraph nodes, with citations. An LLM is optional and may only *reword* that grounded draft. The student picks the mode
on **Sources → Privacy & AI** (default: **Local**; override the initial mode with `LLM_MODE` in `.env`):

| Mode | What runs | Leaves the device? |
|---|---|---|
| **Off** | Nothing — deterministic grounded answers | No |
| **Local** (default) | Any OpenAI-compatible server on `localhost` (Ollama, LM Studio, llama.cpp) | No |
| **Cloud** | OpenRouter (or Anthropic direct) | Yes: the question + MentorIA's draft answer |

What an LLM receives in local/cloud mode: only the question and the drafted answer (concept names, estimates, deadlines,
and the email/assignment titles it cites). Raw emails, PDFs and the database are never sent. OpenRouter requests ask it to
route only to providers that don't collect data (`provider.data_collection = "deny"`) unless `OPENROUTER_ALLOW_DATA_COLLECTION=true`.

**Guardrail:** a rewrite is discarded, and the grounded draft is shown instead, if it adds any number that isn't in the draft
or drops any cited question (Q2, Q3…) or bolded topic/event. Chat shows which model worded each answer, or why it was skipped.
Known limit: the guardrail doesn't catch a dropped *sentence* (e.g. a disclaimer); the Caveats list under each answer is
never reworded.

**Local setup (Ollama):**
```bash
ollama pull qwen2.5
ollama serve
```
Then choose **Local model** on the Sources page. Measured on an M-series Mac with 16 GB of memory: `qwen2.5` (7B) takes
5–25 s per answer; `llama3.2` (3B) takes about 3–8 s but more of its rewrites get discarded by the guardrail.
If Ollama isn't running or the model isn't installed, Local mode falls back to the grounded draft within about 1.5 s and the chat says why.
For the snappiest live demo, switch to **Off**; it answers instantly.

**OpenRouter setup:** set `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` (any id from openrouter.ai/models) in `.env`, restart the API, then choose **Cloud model**.

## Demo script (4 min)
1. **Dashboard** (prepopulated): 3 courses · 48 concepts; your goal (2 sources); Focus: Backpropagation, Policy Gradients.
2. **Ask** "What ML topics am I struggling with?" → Backpropagation 0.12 citing 10-601 Quiz 2 **and** 10-605 lecture quizzes.
3. **Student Model** → 10-605 concepts marked "shared with 10-601": one concept, evidence from both courses.
4. **About me** → "I want a job at a startup that makes robots understand language" → goal now **3 sources**; matching concepts and opportunities listed.
5. **Ask** "Events to attend?" → language-robotics seminar and startup mixer on top; quant club filtered out.
6. **Calendar → Open calendar → ✨ Plan my week** → dashed study blocks in free time before HW deadlines; click one → Approve → *Simulated*, block turns solid.
7. Click any dashboard item for its details (reasons, evidence, links).

## Integration status (truthful)

| Source | Status | Notes |
|---|---|---|
| Canvas | **MOCK_ONLY** | REST adapter implemented (`connectors/canvas.py`), not tested live: no credentials were available. Demo data is added from files. |
| Google Calendar read | **MOCK_ONLY** | Adapter + token refresh implemented, untested live. |
| Google Calendar write | **MOCK_ONLY** | Approved writes are *simulated* and labeled unless `GOOGLE_CALENDAR_WRITE_ENABLED=true` and the token has `calendar.events` scope. Idempotent via private extended property. Untested live. |
| Gmail | **MOCK_ONLY** | Read-only, query-filtered, bodies clipped. Untested live. |
| Piazza | **MOCK_ONLY** | No official API; optional unofficial `piazza-api` path behind `PIAZZA_ENABLED`. Untested. |
| PDF upload | **Working** | Tested with generated demo PDFs (graded + ungraded). Text-based PDFs only (no OCR). |
| LLM — local (Ollama) | **Working** | Tested live with `qwen2.5` and `llama3.2` through the running app. |
| LLM — OpenRouter | **MOCK_ONLY** | Request shape tested against a fake server; no real call made (no key available). |
| LLM — Anthropic direct | **Untested** | Optional alternative cloud provider. |

To connect real services: copy `.env.example` to `.env`, fill in credentials, run `backend/.venv/bin/python scripts/google_auth.py` for Google, restart, and press **Sync all**. A card changes to `connected` / `verified_live: true` only after a successful live call. Failures show `failed` with the error plus labeled fixtures; other cards are unaffected.

## Architecture
- `backend/app/connectors/` adapters → `services/aggregation.py` (sync, dedup on `(provider, external_id)`, isolate failures).
- `services/document_ingest.py`: PDF → page text → per-question grading markers → `Observation`s (pending review when ambiguous).
- `memory/`: immutable observations, `updates.py` (the only writer of beliefs; BKT replay), `context.py` (student model, graph, narrative, `/api/memory/context`).
- `orchestration/graph.py`: LangGraph `route → memory_update? → {struggling | weekly_focus | course_next | opportunities | sources | general} → compose`.
- `services/planning.py`, `opportunity_ranking.py`, `actions.py` (approval validation + idempotent execution).
- `frontend/`: Vite + React + TS; pages Dashboard, Student Model, Documents, Sources; persistent chat panel.

## Testing
- Automated: `cd backend && .venv/bin/python -m pytest -q` (52 tests) and `npm --prefix frontend run build`.
- Manual: [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md), a 90-step checklist covering every feature.

## Known gaps
- **No live connector verified.** Canvas, Google Calendar/Gmail and Piazza adapters exist but have never made a real call. Data is added from files.
- **Course overviews need MentorIA's format.** Concepts come from `Concept:` lines; a real syllabus PDF won't define concepts yet (roadmap: extraction with student review).
- **Goal extraction is pattern-based.** "I want to…", "I'm interested in…", "I prefer…"; the About me tab saves anything else as the closest category or a note.
- **Keyword intent routing.** Phrasings outside the main question types get a general summary, and some overlap (e.g. "What's due this week?" goes to the weekly plan).
- **BKT is uncalibrated.** Slip, guess and learn parameters are illustrative; there's no forgetting over time beyond a 60-day "stale" flag.
- **PDF parsing is narrow.** It needs explicit `Topic:` and `Result:`/`Score:` lines per question. There's no OCR for scanned PDFs, and questions spanning a page break aren't parsed.
- **LLM guardrail is partial.** It catches added numbers and dropped citations or topics, not dropped sentences. Local rewording adds 5–25 s per answer.
- **Single-user local demo.** The API has no auth; the database isn't encrypted.

## Next steps & roadmap

### 1. Before the live demo (hours)
- [ ] Run the manual guide end to end ([docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md)) and fix anything that fails.
- [ ] Decide the demo AI mode: **Off** (instant, deterministic) or **Local** (privacy story, slower). Pre-warm Ollama with one question so the first answer isn't cold.
- [ ] Rehearse the demo script; record a backup screen capture in case of Wi-Fi or laptop issues.
- [ ] Tune `fixtures/synthetic_world.md` to tell the story you want (your courses, a talk that fits the judges' interests).

### 2. Real data (first week after)
- [ ] **Canvas live read:** create a token, sync, and fix whatever the first real response breaks. Mark verified only after a successful call.
- [ ] **Google Calendar + Gmail:** create an OAuth client, run `scripts/google_auth.py`, verify reads, then test one approved calendar write end to end (and confirm it's created exactly once).
- [ ] **Concept map for real courses:** generate concepts per course from the syllabus PDF or Canvas modules, with student review before they're used. This is what connects real assignments to evidence.
- [ ] **Real graded work:** extend PDF parsing to common real formats (Gradescope exports, ✓/✗ marks, "x/y pts" per question). Anything ambiguous goes to a review queue instead of being guessed.
- [ ] **Review queue UI:** let the student accept, edit or reject "pending review" answers (e.g. partial credit, inferred topics) so they can count.
- [ ] **Piazza:** only if needed; it's an unofficial API, so keep it behind the flag.

### 3. Smarter, still grounded (weeks)
- [ ] **LLM-assisted intent routing** with the keyword router as a fallback, so free-form questions land in the right place; log misroutes to improve the rules.
- [ ] **Stronger rewrite guardrail:** also require kept caveats and disclaimers, or have the model output structured fields that MentorIA renders itself.
- [ ] **Conversation memory:** use chat history for follow-ups ("what about the second one?").
- [ ] **Forgetting / spaced review:** add decay (e.g. an FSRS-style recall estimate) as a separate signal next to BKT, plus "review again" suggestions.
- [ ] **Calibrate BKT** per course once enough real graded answers exist; show confidence intervals rather than single numbers.
- [ ] **Better planning:** respect stated study preferences (time of day, block length), avoid stacking blocks, balance across courses, and re-plan when the calendar changes.
- [ ] **Course recommendations from a real catalog:** ingest a department catalog or degree audit and match it against goals and evidence, citing catalog pages for every claimed prerequisite.
- [ ] **Semantic search** over documents (local embeddings) for "where did we cover X?" questions with page citations.

### 4. Proactive & multi-source (later)
- [ ] Background sync on a schedule with a "what changed since yesterday" digest.
- [ ] More sources: Gradescope, Google Drive/Docs notes, course websites, university event feeds.
- [ ] Notifications for approval-worthy items (a matching talk, a deadline at risk), still never acting without approval.
- [ ] Post-session check-ins ("How did the cache coherence block go?") feeding engagement and confidence, never mastery.

### 5. Privacy, security & production (before real users)
- [ ] User accounts and per-student data isolation; auth on every API route.
- [ ] Encrypt the local database and token file at rest; one-click "export my data" and "delete everything".
- [ ] Per-source consent screens and a visible log of what each connector read.
- [ ] Optional redaction (names, emails) before anything goes to a cloud LLM; make Local the only option for sensitive sources.
- [ ] Packaging: a one-command install (e.g. Docker Compose with Ollama) and a desktop build.
- [ ] CI that runs the backend tests and frontend build on every push.
