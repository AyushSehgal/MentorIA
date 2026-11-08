# MentorIA Task Board

Statuses: TODO, CLAIMED, IN_PROGRESS, BLOCKED, READY_FOR_REVIEW, DONE, MOCK_ONLY. One owner per task.

| ID | Pri | Deliverable | Deps | Owner | Status | Files owned | Acceptance test | Commit |
|---|---|---|---|---|---|---|---|---|
| T00 | P0 | Repo bootstrap, scripts, .env.example, coordination | – | coordinator | DONE | root, coordination/, scripts/ | API + UI boot locally | |
| T01 | P0 | Contracts (TS+Pydantic), fixtures, SQLite | T00 | coordinator | DONE | frontend/src/api/types.ts, backend/app/schemas.py, backend/app/db.py, fixtures/ | Example payloads validate | |
| T02 | P0 | Dashboard shell, 5 source widgets, embedded chat | T01 | frontend-agent | DONE | frontend/** (except src/api/types.ts) | Cards render with demo labels | |
| T03 | P0 | Connector adapters + aggregate endpoint | T01 | coordinator | DONE | backend/app/connectors/, services/aggregation.py | Dashboard grouped; failures isolated | |
| T04 | P0 | PDF upload + page-referenced extraction | T01 | coordinator | DONE | backend/app/services/document_ingest.py | Quiz PDF appears with page refs | |
| T05 | P0 | Episodic store + BKT + confidence + context | T01,T04 | coordinator | DONE | backend/app/memory/ | Evidence updates one concept; idempotent | |
| T06 | P0 | LangGraph router + grounded /api/chat | T03,T05 | coordinator | DONE | backend/app/orchestration/ | Weak-topic + weekly-focus answers cite evidence | |
| T07 | P0 | Recommendation + approval | T06 | coordinator (API) / frontend-agent (UI) | DONE | backend/app/api/recommendations.py, ApprovalCard.tsx | Reject never writes | |
| T08 | P0 | E2E integration + seed/reset | all P0 | coordinator | DONE | scripts/, README.md | Live UI source→memory→chat→rec | |
| T09 | P1 | Real Canvas read adapter | T03 | coordinator / student-model-agent | DONE (live: canvas.cmu.edu, 2026-11-07; known issues in SCRATCHPAD) | connectors/canvas.py, config.py | Verified live assignment | |
| T10 | P1 | Real Calendar read + approved write | T03,T07 | coordinator / student-model-agent | DONE (live read + one approved write, created exactly once; 2026-11-07) | connectors/google_calendar.py | Verified read; approved write once | |
| T11 | P1 | Real Gmail read + talk extraction | T03,T05 | coordinator / student-model-agent | DONE (live read -> ranked opportunities; 2026-11-07; known issues in SCRATCHPAD) | connectors/gmail.py, services/opportunity_ranking.py | Verified message → opportunity card | |
| T12 | P1 | Piazza adapter (best effort) | T03 | coordinator | MOCK_ONLY | connectors/piazza.py | Live discussion or honest fallback | |
| T13 | P1 | Propositions + derived narrative | T05 | coordinator | DONE | memory/propositions.py | Goal reflected in chat context | |
| T14 | P1 | Graph view / relation list | T05 | frontend-agent | DONE | frontend/src/pages/Knowledge.tsx | Inspect concept/evidence links | |
| T15–T17 | P2 | Advanced grading extraction, FSRS, tutoring | – | – | TODO | – | Only after demo stable | |
| T18 | P1 | Student Model section (page, graph, model/graph API) | T05,T14 | student-model-agent | IN_PROGRESS (merged into main 2026-11-07; see SCRATCHPAD) | frontend/src/pages/Knowledge.tsx, frontend/src/components/student-model/** (was components/KnowledgeGraph.tsx), frontend/src/pages/knowledge.css (new), backend/tests/test_student_model.py (new), backend/app/memory/context.py (`student_model`, `graph`, `narrative` only), backend/app/api/memory.py | Student Model page works on branch `student-model`; dashboard cards unchanged; pytest + `npm run build` pass | |
| T19 | P1 | Main Dashboard section (cards, insights, chat panel, approvals UI) | T02,T07 | coordinator | DONE (on main: compact blocks, Quick Recap + suggestions, calendar, About me tab) | frontend/src/pages/Dashboard.tsx, frontend/src/components/{ChatPanel,ApprovalCard}.tsx, frontend/src/pages/dashboard.css (new), backend/app/services/dashboard.py | Dashboard works; Student Model page unchanged; pytest + `npm run build` pass | |
| T20 | P1 | About me moves to Student Model (Dashboard chat = Ask only); About me answers questions about the student; calmer concept map | T18,T19 | student-model-agent | READY_FOR_REVIEW | frontend/src/components/student-model/**, frontend/src/pages/{Knowledge.tsx,knowledge.css}, frontend/src/components/ChatPanel.tsx + frontend/src/pages/Dashboard.tsx (one prop; approved by the Dashboard owner), backend/app/orchestration/{graph.py,tools.py,nodes.py} (tell-mode questions only; approved), backend/tests/test_student_model.py | Dashboard chat has no About me tab; Student Model shows belief summary + About me chat; a question in About me is answered and not saved; pytest + `npm run build` pass | |
| T21 | P1 | Live Ed Discussion read adapter (best effort; undocumented API) | T03 | student-model-agent | DONE (live read: 30 threads from 11-868, 2026-11-07) | connectors/edstem.py (new), connectors/__init__.py, services/aggregation.py (PROVIDERS), config.py, .env.example, frontend/src/lib/format.ts (label), backend/tests/test_edstem.py (new) | Verified live thread appears in Relevant Discussion; private threads skipped | |

### Shared files during T18/T19 (additive changes only; announce in SCRATCHPAD before editing)
- `frontend/src/api/types.ts` + `backend/app/schemas.py`: new optional fields/types only; no renames or removals (AGENTS.md rule 3 still applies).
- `frontend/src/styles.css`, `components/Common.tsx`, `lib/format.ts`, `api/client.ts`: add new exports/classes only. Put section styles in the new per-page CSS files.
- `frontend/src/App.tsx` (nav/routing): ask before editing.
- `backend/app/memory/context.py` `concept_states()` / `concept_state()`: used by dashboard insights and weekly planning. Keep their output and behavior unchanged; add a new function or optional parameter instead.
- **Exceptions already on main (deliberate, recorded 2026-11-07 at merge of `student-model`):**
  - `App.tsx` was edited on main without the ask-first step: Add data nav hidden, header connector dots and demo badge removed (ADR-013 + later UI requests).
  - `concept_states(course_id)` now also returns concepts *shared* with that course (`ConceptState.also_in`, contract v1.4), so a 10-605 view includes Backpropagation etc. Output for unshared concepts is unchanged. Dashboard insights and planning rely on this.
