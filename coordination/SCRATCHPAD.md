# MentorIA Scratchpad (append-only)

[2026-11-07 14:15 EST] coordinator | T00/T01 | START
Files: root config, coordination/, frontend/src/api/types.ts, backend/app/schemas.py
Contract assumptions: CONTRACTS.md v1 frozen before parallel work.
Blockers: no Canvas/Google/Piazza/LLM credentials present in environment → all connectors start in demo_data mode.
Next handoff: frontend-agent builds UI against types.ts + CONTRACTS.md.

[2026-11-07 14:20 EST] frontend-agent | T02/T07-UI/T14 | START
Files: frontend/** (except src/api/types.ts)
Contract assumptions: CONTRACTS.md v1 + types.ts as frozen.
Blockers: none

[2026-11-07 14:45 EST] frontend-agent | T02/T07-UI/T14 | READY_FOR_REVIEW
Files: frontend/{package.json,package-lock.json,tsconfig.json,vite.config.ts,index.html}, frontend/src/{main.tsx,App.tsx,styles.css}, src/api/client.ts, src/lib/format.ts, src/components/{Common,ApprovalCard,ChatPanel,KnowledgeGraph}.tsx, src/pages/{Dashboard,Knowledge,Documents,Sources}.tsx
Tests: `npm run build` passes (tsc strict, 0 errors). Smoke: UI renders with backend down (banner + per-card error, chat still usable). Not yet verified against live backend payloads.
Interfaces changed: none (types.ts untouched).
Needs integration: run `npm run dev` (port 5173, /api proxied to :8000). Chat history persists across route changes (module-level). Knowledge page refetches model/graph/history independently.
Contract notes: (1) calendar end time read from metadata.end (ISO) if present; (2) Canvas course name from metadata.course_name, completion from metadata.completed; (3) Piazza instructor flag metadata.is_instructor; (4) MentorIA-created calendar events flagged by metadata.created_by_mentoria.

[2026-11-07 15:30 EST] coordinator | T00–T08, T13 | DONE
Files: backend/**, scripts/{dev.sh,seed_demo.py,make_demo_pdfs.py,google_auth.py}, fixtures/**, README.md
Tests: pytest 18/18 pass (BKT, idempotency, order independence, self-report isolation, graded/ungraded PDFs, connector partial failure, fixture labels, chat source refs, no-catalog honesty, goal→proposition, reject/approve idempotency, exact-confirm, undated opportunity, untrusted email text, smoke routes).
Manual: live UI at :5173 against API :8000 — dashboard, weekly-focus chat with approval cards, approve → "Simulated" label, Student Model + graph, Documents table; mobile 375px no horizontal scroll; no console errors.
Interfaces changed: added HealthResponse/LLMInfo to schemas.py (matches types.ts HealthResponse). Frontend contract notes (metadata.end, course_name, completed, is_instructor, created_by_mentoria) all match backend.
Needs integration: T09–T12 live connectors are MOCK_ONLY — need real credentials in .env.

[2026-11-07 15:30 EST] coordinator | T02/T07-UI/T14 | REVIEWED
Verified frontend against live backend payloads; accepted.

[2026-11-07 16:10 EST] coordinator | synthetic-md | DONE
Files: fixtures/synthetic_world.md (new, single source), backend/app/synthetic.py (parser), connectors/base.py, memory/catalog.py,
memory/context.py, services/seed.py, api/sources.py, config.py; removed fixtures/{source_records,student_profile,knowledge_graph}.json
Tests: pytest 24/24 (6 new: parse, bad reference error, edit→sync, removal→sync, invalid edit keeps last good, new self-report row).
Manual: running API — edited a calendar row in the md, Sync all → dashboard showed the edit; reverted.
Interfaces changed: none (API contract unchanged). New env var MENTORIA_SYNTHETIC_FILE.

[2026-11-07 16:50 EST] coordinator | llm-privacy | DONE
Files: backend/app/orchestration/llm.py, graph.py, config.py, schemas.py, api/sources.py, db.py; frontend types.ts, client.ts, ChatPanel.tsx, pages/Sources.tsx, styles.css
Tests: pytest 33/33 (9 new LLM tests with a fake OpenAI-compatible server). Frontend build passes.
Live: Ollama qwen2.5 + llama3.2 through the running app; guardrail rejected some rewrites (dropped Q-citations) as intended.
OpenRouter: MOCK_ONLY (no key). Mode left at "off".
Interfaces changed: contract v1.1 (additive) — see CONTRACTS.md.

[2026-11-07 17:05 EST] coordinator | llm-default-local | DONE
Default LLM mode changed off → local (config, .env.example, README, ADR-009 amendment). Running instance switched to local.
Tests: 36/36 (3 new: default is local, fresh install reports local, local default with no server still answers).

[2026-11-07 17:30 EST] frontend-agent | v1.2-ui | START
Files: frontend/src/** (except api/types.ts)

[2026-11-07 17:55 EST] frontend-agent | v1.2-ui | READY_FOR_REVIEW
Files: frontend/src/api/client.ts (demoAssets, addDemoAsset, importFile, imports), App.tsx (nav "Add data"),
pages/Documents.tsx (rebuilt as Add data: demo assets w/ Add / Add again / Add all remaining + inline ImportResult,
upload w/ "I wrote this" + dynamic course select, import history, graded-doc question tables), pages/Dashboard.tsx
("What MentorIA knows" bar with growth highlight, empty hero, per-card empty states, goal insight icon), pages/Knowledge.tsx
(no-courses empty state, proposition source chips + "stated in N sources"), components/Common.tsx (mode "import" → "from files"),
components/ChatPanel.tsx (new chips + helper text), pages/Sources.tsx (reset/verified copy), styles.css (imported dot/badge, new blocks).
Tests: npm run build passes (tsc strict, 0 errors). Not verified against v1.2 backend (routes not live yet).
Interfaces changed: none (types.ts untouched).

[2026-11-07 18:30 EST] coordinator | v1.2 empty-start + v1.3 about-me + rename | DONE (backend)
Files: backend/app/{services/imports.py,services/demo_assets.py,demo_content.py,memory/catalog.py,memory/propositions.py,
orchestration/*,services/dashboard.py,schemas.py}, tests/{conftest.py,test_imports.py,test_synthetic.py}, README, .env.example
Tests: pytest 50/50. Scripted walkthrough of all 14 assets verified (goal merges to 3 sources; ranking; weekly plan).

[2026-11-07 frontend-agent | ui-compact + about-me | DONE
Files: frontend/src/{pages/Dashboard.tsx, components/Common.tsx (Block, MoreList, Item, Why), components/ChatPanel.tsx (Ask / About me tabs, mode "tell"), components/ApprovalCard.tsx (compact; label now "Approve"), lib/format.ts (fmtShort, fmtDay), pages/Documents.tsx, pages/Knowledge.tsx, pages/Sources.tsx, styles.css}
Tests: `tsc --noEmit` clean for src; `vite build` passes. `npm run build` currently fails only on frontend/vite.config.ts (process.env without @types/node) — edited outside this task.
Interfaces changed: none (types.ts untouched). Dashboard hides source blocks entirely while knowledge counts are all 0 (shows only "MentorIA is empty / Add data").

[2026-11-07 19:10 EST] coordinator | rename + about-me + compact UI | DONE
Verified in browser (API :8001 + UI :5180): empty state, Add all remaining (14 assets), compact blocks, About me example →
goal pill "3 sources". Course ids now "10-601"/"16-831". pytest 50/50, frontend build passes. Testing guide rewritten (61 checks).

[2026-11-07 19:40 EST] frontend-agent | v1.4 hide add-data, no demo labels, shared concepts | START
Files: frontend/src/** (not types.ts)

[2026-11-07 19:55 EST] frontend-agent | v1.4 hide add-data, no demo labels, shared concepts | DONE
Files: frontend/src/{App.tsx,components/Common.tsx,components/ApprovalCard.tsx,components/WeekCalendar.tsx,pages/Dashboard.tsx,pages/Documents.tsx,pages/Knowledge.tsx,pages/Sources.tsx,styles.css}
Build: npm run build passes. No user-visible "demo" text remains in frontend/src (only identifiers/routes).
Note: backend-provided strings (connector details, venues, chat caveats) must also avoid "demo" — backend scope.

[2026-11-07 20:00 EST] coordinator | 10-605 + prepopulate + no-demo-labels | DONE
16 sample files (10-605 overview + lecture quizzes added); shared concepts via also_in; prepopulate on startup/reset;
backend "demo" wording removed. pytest 52/52; browser: prepopulated dashboard, no "demo" text, 12 shared pills.
[2026-11-07 15:33 EST] student-model-agent | T18 | START
Branch: student-model (from main @ dff9485)
Files: frontend/src/pages/Knowledge.tsx, frontend/src/components/KnowledgeGraph.tsx, frontend/src/pages/knowledge.css (new),
backend/app/memory/context.py (student_model/graph/narrative only), backend/app/api/memory.py
Contract assumptions: CONTRACTS.md v1.2. Shared files are additive-only (see TASKS.md "Shared files during T18/T19").
Coordination: dashboard-agent owns T19 (Dashboard). concept_states() behavior stays fixed because dashboard insights and planning use it.
Baseline: pytest 36/36 pass; frontend `npm run build` passes.
Blockers: none

[2026-11-07 15:55 EST] student-model-agent | T18 | READY_FOR_REVIEW (graph-first Student Model page, v1)
Branch: student-model
Files: frontend/src/pages/Knowledge.tsx (rewritten: Map / Timeline / Details tabs + inspector), frontend/src/pages/knowledge.css (new, sm- prefix),
frontend/src/components/student-model/{replay.ts, ConceptMap.tsx (moved from components/KnowledgeGraph.tsx), Inspector.tsx, Timeline.tsx, Details.tsx},
backend/app/api/memory.py (self_confidence event_id now unique per request), backend/tests/test_student_model.py (new).
Tests: pytest 37/37 (new: rapid confidence updates all apply; fails without the fix). `npm run build` passes.
Manual (isolated API on a scratch DB + demo assets 01,02,03,05,06,07,08): frontend BKT replay matches backend mastery for all 8 graded
concepts and the blind-spot flag; replay slider, timeline, details, goal confirm, keyboard confidence edits, 375px width. No console errors on load.
Interfaces changed: none (types.ts / schemas.py untouched; no API shape change). Shared files untouched.
Notes: replay recomputes BKT in the browser from /api/memory/history using the same params/order as backend (replay.ts mirrors bkt.py,
ADR-005, ADR-007). If bkt.py params change, update replay.ts too. Running :8000 servers need a restart to pick up the memory.py fix.

[2026-11-07 21:00 EST] coordinator | merge origin/student-model (T18) into main | DONE
Decisions (confirmed by the user): Juan's graph-first Student Model page replaces main's list page; main's decisions ported into it:
MentorIA naming, no visible "Demo" chips/labels (ADR-013), no "Add data" mention, shared concepts (also_in) linked to every
course hub on the map, shown under each course in Details ("shared" pill + both codes) and in the inspector.
T19 marked DONE on main (no pending dashboard branch). Shared-file rules kept; main's App.tsx / concept_states changes logged as exceptions in TASKS.md.
Conflicts resolved: Knowledge.tsx (took student-model, then ported), SCRATCHPAD.md (kept both logs).
Tests: pytest 54/54 (incl. test_student_model.py); npm run build passes.

[2026-11-07 21:30 EST] coordinator | dashboard: assignments tags/sort, course forums, remove opportunities+documents | DONE
Contract v1.6 (edstem provider, course_message emails, DashboardResponse.discussions). Sample Ed posts (10-605) and a
[10-601] staff email added (18 sample files). pytest 55/55; browser-verified.
Note: which forum each real course uses (Piazza vs Ed) is not verified — the Ed posts are sample data.

[2026-11-07 21:50 EST] coordinator | Relevant Discussion dropdown + dark mode | DONE
Discussions block renamed "Relevant Discussion", collapsed by default (course counts summary). Dark theme via
html[data-theme] (index.html applies saved/OS theme before paint; header toggle saves to localStorage); dark palette +
overrides for every hard-coded light colour (styles.css). Verified in browser in both themes.

[2026-11-07 22:05 EST] coordinator | assignment complete toggle | DONE
POST /api/assignments/{id}/complete (contract v1.7); choice persisted in meta and re-applied on every upsert so syncs/imports
can't undo it; workload recomputed. Dashboard: round check button per row, strikethrough, "done" tag; toggled rows stay
in place until reload. pytest 56/56; browser-verified complete + undo.

[2026-11-07 22:30 EST] coordinator | clearer weekly-focus answer | DONE
weekly_focus rewritten as a short story (graded evidence -> next lecture + deadline -> suggested readings -> one secondary
item -> study block), built from records, not hardcoded. Sample data: lecture topics on calendar events (10-601/16-831 in
public-schedule order; 10-605 real Nov 9/11 lectures), concept tags on calendar events, 10-601 suggested readings
(Goodfellow §6.5, Bishop §5.3) explicitly labeled as not course-assigned. pytest 56/56; browser-verified.

[2026-11-07 16:38 EST] student-model-agent | T20 | START
Branch: student-model (from main @ 73f491b). Approved by the Dashboard owner (Ayush) for the shared/owned files below.
Files: components/student-model/** + pages/{Knowledge.tsx,knowledge.css} (mine); ChatPanel.tsx (+optional `modes` prop, About me chips),
Dashboard.tsx (passes modes={["ask"]}); orchestration/{graph.py,tools.py,nodes.py}: in tell mode, a question about the student is
answered from the model (new about_me node) and never saved; statements are saved exactly as before.
Contract: no schema change (about_me answers use the existing intent "general"; ChatRequest.mode unchanged). Behavior note goes in CONTRACTS v1.8.

[2026-11-07 16:43 EST] student-model-agent | T20 | READY_FOR_REVIEW
Files: backend/app/orchestration/{tools.py (is_self_question), graph.py (route tell questions -> about_me), nodes.py (about_me)},
backend/tests/test_student_model.py (+4), frontend/src/components/ChatPanel.tsx (modes prop; About me question chips; dropped the
"not confident"/"feeling" prefills and the long example chip), frontend/src/pages/Dashboard.tsx (modes={["ask"]}),
frontend/src/components/student-model/{AboutMe.tsx (new), ConceptMap.tsx (focusIds calm view, legend), replay.ts (mastery rounded
to 3 dp like the backend)}, frontend/src/pages/{Knowledge.tsx, knowledge.css}, coordination/{CONTRACTS v1.8, DECISIONS ADR-014}.
Tests: pytest 61/61 (new: question answered not saved; self-report-looking questions not saved; "What I…" statements saved;
honest empty overview). `npm run build` passes.
Browser (isolated API :8001 on a scratch DB, prepopulated): calm map 13 topics vs 48 with All topics; About me "What do you know
about me?" answered with 0 new observations; "I'm confident about backpropagation" -> blue ring + red dot + "Check this" row live;
chat and inspector agree (0.12); Dashboard chat shows "Ask MentorIA" only; dark mode; 900px stacks. No console errors.
Interfaces: no schema change (intent "general" reused). Running :8000 API needs a restart for the backend part.

[2026-11-07 18:52 EST] student-model-agent | T09 Canvas live | DONE
Live: https://canvas.cmu.edu with a personal access token in .env (never committed). POST /api/connectors/canvas/sync ->
connected / verified_live: true, "Live read OK (71 records)", no errors. Re-verified after the change below: 46 records, 0 excluded.
Change: CANVAS_EXCLUDE_COURSES (config.py, connectors/canvas.py, .env.example): comma-separated Canvas course names, codes or ids
(exact, case-insensitive) that are never synced; applied before the 12-course cap. Tests: backend/tests/test_canvas.py (fake Canvas),
pytest 63/63. The 25 "Machine Learning in Production" records were also deleted from the local DB (user request).
Known issues, NOT fixed (decision pending):
- course_for_text matches loose aliases, so a real "Machine Learning in Production" course mapped to course_id 10-601. Match by
  course number instead.
- 46 of the live assignments have no due date (orientation/career "courses"): clutter in Assignments ("+N more").
- concept_ids are matched on description text across all courses, e.g. a real Homework 6 linked to advanced_rl.
- Live and sample Canvas items show side by side with no visible distinction (ADR-013 removed demo labels).

[2026-11-07 19:20 EST] student-model-agent | T10 Google Calendar + T11 Gmail live | DONE
Setup: Google Cloud project (External, Testing), Desktop OAuth client; scripts/google_auth.py --calendar-write (scopes
calendar.readonly, gmail.readonly, calendar.events); token in backend/data/google_token.json (gitignored, chmod 600);
GOOGLE_CALENDAR_WRITE_ENABLED=true. No code changes.
Live: google_calendar sync -> connected / verified_live, 23 events (Nov 9-13); gmail sync -> connected / verified_live, 15 messages.
Planner re-planned around real events (backprop block moved to Mon 1:50 PM, after a real 1:00-1:50 meeting).
Approved write: rec_study_backpropagation_20261109 -> executed (not simulated); Google Calendar API shows exactly 1 event with
mentoria_recommendation_id; a second approve returned "Already processed" and the count stayed 1.
Gmail -> opportunities: 15 live emails ranked; top: brAIn Seminar (0.80), timing honestly "no time found".
Known issues, NOT fixed:
- Pending study proposals made before a calendar sync stay pending with stale times (one clashes with a real class).
- Gmail query is broad: personal threads mentioning "lecture"/"talk" are imported (privacy on stage).
- Time parsing misses formats like "3:30p"; past seminars still listed as "worth reviewing".
- Live and sample calendar events are mixed; sample events count as busy time.

[2026-11-07 19:40 EST] student-model-agent | T21 Ed Discussion live | START
Files: connectors/edstem.py (new), connectors/__init__.py, services/aggregation.py (+ "edstem" in PROVIDERS), config.py
(EDSTEM_BASE_URL, EDSTEM_API_TOKEN, EDSTEM_EXCLUDE_COURSES), .env.example, frontend lib/format.ts (providerLabel "Ed Discussion",
additive), backend/tests/test_edstem.py (new). Contract: none ("edstem" provider and discussion records exist since v1.6).
Probe (read-only): GET /api/user and /api/courses/{id}/threads on us.edstem.org with a personal token -> 200.

[2026-11-07 19:55 EST] student-model-agent | T21 Ed Discussion live | DONE
Live (read-only, personal token): EdStemConnector().fetch_live -> 30 threads from "11-868 Large Language Model Systems",
14 staff/announcement, private threads skipped. Records: provider "edstem", kind "discussion", metadata.course_name "11-868 …",
is_instructor (admin/staff/mentor/tutor or announcement), course_id only on an exact MentorIA course-number match (none today).
Tests: backend/tests/test_edstem.py (fake Ed). Needs an API restart before "Sync all" includes Ed.

[2026-11-07 19:55 EST] student-model-agent | INCIDENT: tests used the real .env | FIXED
config.py loads the developer's .env at import, so once Google was signed in, pytest ran live: test_connector_partial_failure
read real Gmail, and test_approval_idempotent created ONE real Google Calendar event ("Study: Cache Coherence (MESI) before
Cache Lab Part B", Sun Nov 8 3:20 PM). Fix: autouse fixture `no_real_credentials` in tests/conftest.py blanks every external
credential (Canvas, Google, Ed, Piazza, OpenRouter, Anthropic) for every test. Verified: full suite 67/67 with a socket guard
that blocks all non-localhost connections (guard confirmed active). Stray event reported to the user; not deleted without OK.
[2026-11-07 20:00 EST] student-model-agent | INCIDENT follow-up | Stray test event deleted from Google Calendar with the user's OK
(event vgenvq283mukboj3m4cq3le9o0, rec_study_cache_coherence_20261108). The user's kept "Study: Backpropagation" event is untouched.

[2026-11-07 20:20 EST] student-model-agent | chat: discussions answer + Anthropic Sonnet | READY (key pending)
Files: orchestration/tools.py (route "discussions" before struggling/weekly_focus), orchestration/nodes.py (new `discussions`
node; `sources` instructor posts now Piazza + Ed), orchestration/graph.py (capability; reported intent "sources"),
orchestration/llm.py (anthropic mode requires ANTHROPIC_API_KEY), backend/tests/test_discussions.py (new), CONTRACTS v1.9.
Why: "Summarize what happened on Ed this week" hit weekly_focus ("this week"); "announcements" read Piazza only.
LLM: local mode never ran (Ollama has llama3.1, config expects qwen2.5). Per user: cloud via Anthropic, model claude-sonnet-5-5
(.env LLM_CLOUD_PROVIDER=anthropic). Key to be pasted by the user. Tests: 70/70 with an outside-network guard.

[2026-11-07 20:35 EST] student-model-agent | chat: discussions answer + Anthropic Sonnet | DONE (live)
Running API restarted with ANTHROPIC_API_KEY; privacy mode set to cloud (user request) -> "Anthropic API · claude-sonnet-5-5".
Live checks: "Summarize what happened on Ed this week" -> route:discussions, 17 posts in 7 days (7 staff), grouped by course,
7 linked sources, compose+anthropic:claude-sonnet-5-5 (guardrail accepted), 3.7 s. "What ML topics am I struggling with?" ->
Sonnet rewrite accepted, 2.4 s. Note: the Ed answer mixes live 11-868 posts with sample 10-605 Ed posts (no visible label).
For the live demo, switch the mode back to Off (Sources -> Privacy & AI).

[2026-11-07 20:50 EST] student-model-agent | sample-data labels (ADR-015) | DONE
Files: frontend components/Common.tsx (+SampleTag, chip label), styles.css (+tag-sample, chip-sample, wcal-ev.is-sample,
sm-sample-note; dark variants), pages/Dashboard.tsx (assignment/discussion rows + all-sample groups), components/WeekCalendar.tsx
(dashed sample events, tag in detail), student-model/{Inspector,Details,AboutMe}.tsx, pages/Knowledge.tsx (note);
backend orchestration/nodes.py (_demo_caveat restored as a sample caveat; "sample data" tag in forum summaries).
Verified in the running app: 1 sample assignment row tagged (46 live untagged), 13 of 35 calendar events dashed, Student Model
note + 3 inspector chips + 3 goal chips. pytest 70/70; build passes. Chat caveat needs an API restart.

[2026-11-07 21:10 EST] student-model-agent | deadlines agenda + LLM routing | DONE
Files: orchestration/tools.py (rules), nodes.py (new `deadlines`), graph.py (capability + llm routing, trace router:llm),
llm.py (INTENTS, classify_intent, _parse_label), tests/test_discussions.py (+5). CONTRACTS v1.10, ADR-016.
Tests: 75/75 with an outside-network guard. Live (copy of the real DB, real Sonnet): "Assignments this week" -> router:llm ->
deadlines: Canvas (real + sample), calendar "HW 4 DUE"/"HW6 Due", staff announcements; "anything pressing…" -> deadlines;
"what's going on in my LLM systems class forum?" -> discussions. ~4.5 s per answer (route + rewrite).
Known: course filtering only recognizes MentorIA's catalog courses, so "my LLM systems forum" lists 11-868 first but
does not hide the other courses. Running API needs a restart to pick this up.

[2026-11-07 21:40 EST] student-model-agent | fix: LLM router silently fell back + course narrowing | DONE
Bug: classify_intent used max_tokens=20; Claude Sonnet 5.5 thinks by default and spent it all (empty text, stop_reason
max_tokens), so every question fell back to keywords ("Anything for AI Innovation this week" -> weekly study plan).
Fix (per the Claude API skill): max_tokens 256, output_config effort "low", and on claude-sonnet-5-5 thinking
{"type": "between_tools"} (its only "off" form; "disabled" is a 400); refusal -> fallback. The router prompt now gets the
student's course names (names only) so a course isn't mistaken for an event. Router ~1 s.
New: questions naming a course ("AI Innovation", "11-868", "Large Language Model Systems") narrow the deadlines agenda and the
forum summary to that course, using course names on the synced records (not only MentorIA's catalog).
Tests: 76/76 with an outside-network guard (+1). Live on a DB copy: "Anything for AI Innovation this week" -> router:llm ->
deadlines -> only the 2 AI Innovation assignments (2.9 s). Running API needs a restart.
