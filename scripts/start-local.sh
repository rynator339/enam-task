#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ ! -d "$ROOT/apps/web/node_modules" ]; then
  echo "Frontend modules missing. Run: cd apps/web && npm install"
  exit 1
fi
(cd "$ROOT/apps/api" && uvicorn app.main:app --host 127.0.0.1 --port 8000) &
API_PID=$!
trap 'kill "$API_PID" 2>/dev/null || true' EXIT
(cd "$ROOT/apps/web" && npm run dev)
