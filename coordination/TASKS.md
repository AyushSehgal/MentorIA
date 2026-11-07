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
| T09 | P1 | Real Canvas read adapter | T03 | coordinator | MOCK_ONLY | connectors/canvas.py | Verified live assignment | |
| T10 | P1 | Real Calendar read + approved write | T03,T07 | coordinator | MOCK_ONLY | connectors/google_calendar.py | Verified read; approved write once | |
| T11 | P1 | Real Gmail read + talk extraction | T03,T05 | coordinator | MOCK_ONLY | connectors/gmail.py, services/opportunity_ranking.py | Verified message → opportunity card | |
| T12 | P1 | Piazza adapter (best effort) | T03 | coordinator | MOCK_ONLY | connectors/piazza.py | Live discussion or honest fallback | |
| T13 | P1 | Propositions + derived narrative | T05 | coordinator | DONE | memory/propositions.py | Goal reflected in chat context | |
| T14 | P1 | Graph view / relation list | T05 | frontend-agent | DONE | frontend/src/pages/Knowledge.tsx | Inspect concept/evidence links | |
| T15–T17 | P2 | Advanced grading extraction, FSRS, tutoring | – | – | TODO | – | Only after demo stable | |
