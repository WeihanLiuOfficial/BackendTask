#!/bin/bash
# start.sh — Starts the Boundary AI backend and frontend in separate terminal tabs/processes.
# Run from the BackendTask root directory: bash start.sh
# Prerequisites: Docker running, backend/.env configured, venv created, npm installed.

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "Starting database (docker-compose)..."
docker-compose up -d db

echo "Starting backend on http://localhost:8000 ..."
osascript -e "tell application \"Terminal\" to do script \"cd '$ROOT/backend' && PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload\"" 2>/dev/null \
  || (cd "$ROOT/backend" && PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &)

echo "Starting frontend on http://localhost:3000 ..."
osascript -e "tell application \"Terminal\" to do script \"cd '$ROOT/frontend' && DANGEROUSLY_DISABLE_HOST_CHECK=true npm start\"" 2>/dev/null \
  || (cd "$ROOT/frontend" && DANGEROUSLY_DISABLE_HOST_CHECK=true npm start &)

echo ""
echo "Both servers are starting."
echo "  Backend:  http://localhost:8000/docs"
echo "  Frontend: http://localhost:3000"
