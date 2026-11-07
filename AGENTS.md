# Agent instructions (MentorIA)

1. Read `MentorIA_CLAUDE_IMPLEMENTATION.md`, `coordination/TASKS.md`, `coordination/CONTRACTS.md`, and the latest `coordination/SCRATCHPAD.md` entries before editing.
2. Claim a task in TASKS.md before editing; only touch the files your task owns.
3. Do not change `frontend/src/api/types.ts` or `backend/app/schemas.py` without a logged proposal + ADR.
4. Never commit `.env`, tokens, private mail, or student records. Fixtures must set `is_fixture: true`.
5. Never mark a live integration DONE without a successful live call; otherwise mark `MOCK_ONLY`.
6. Append START/DONE entries to SCRATCHPAD.md with files, tests, interface changes.
