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
