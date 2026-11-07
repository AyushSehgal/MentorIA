#!/usr/bin/env bash
# Start NOVA API (:8000) and web UI (:5173). Ctrl-C stops both.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
[ -d backend/.venv ] || { uv venv backend/.venv --python 3.12 && uv pip install --python backend/.venv/bin/python -r backend/requirements.txt; }
[ -d frontend/node_modules ] || npm --prefix frontend install
backend/.venv/bin/uvicorn app.main:app --app-dir backend --port 8000 &
API=$!
trap 'kill $API 2>/dev/null' EXIT
npm --prefix frontend run dev
