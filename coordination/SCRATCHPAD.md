# NOVA Scratchpad (append-only)

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
Contract notes: (1) calendar end time read from metadata.end (ISO) if present; (2) Canvas course name from metadata.course_name, completion from metadata.completed; (3) Piazza instructor flag metadata.is_instructor; (4) NOVA-created calendar events flagged by metadata.created_by_nova.

[2026-11-07 15:30 EST] coordinator | T00–T08, T13 | DONE
Files: backend/**, scripts/{dev.sh,seed_demo.py,make_demo_pdfs.py,google_auth.py}, fixtures/**, README.md
Tests: pytest 18/18 pass (BKT, idempotency, order independence, self-report isolation, graded/ungraded PDFs, connector partial failure, fixture labels, chat source refs, no-catalog honesty, goal→proposition, reject/approve idempotency, exact-confirm, undated opportunity, untrusted email text, smoke routes).
Manual: live UI at :5173 against API :8000 — dashboard, weekly-focus chat with approval cards, approve → "Simulated" label, Student Model + graph, Documents table; mobile 375px no horizontal scroll; no console errors.
Interfaces changed: added HealthResponse/LLMInfo to schemas.py (matches types.ts HealthResponse). Frontend contract notes (metadata.end, course_name, completed, is_instructor, created_by_nova) all match backend.
Needs integration: T09–T12 live connectors are MOCK_ONLY — need real credentials in .env.

[2026-11-07 15:30 EST] coordinator | T02/T07-UI/T14 | REVIEWED
Verified frontend against live backend payloads; accepted.
