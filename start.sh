#!/usr/bin/env bash
# HireTrack one-command start for macOS and Linux.
#   chmod +x start.sh && ./start.sh
#
# First run (needs internet, about 5-10 minutes):
#   1. creates a Python 3.11 virtual environment in .venv and installs the packages
#   2. downloads the all-MiniLM-L6-v2 language model (about 90 MB) into models/
#   3. installs the frontend packages and builds the frontend into frontend/dist
#   4. seeds the database (600 candidates, 33 jobs, pipeline, staff, projects)
# Later runs start the app in a few seconds and work fully offline.
# The app opens at http://127.0.0.1:8000  (use PORT=8001 ./start.sh for another port)
set -euo pipefail
cd "$(dirname "$0")"
PORT="${PORT:-8000}"

if [ ! -x .venv/bin/python ]; then
  PY=""
  # A specific Python 3.11 can be given with:  PYTHON=/path/to/python3.11 ./start.sh
  for candidate in ${PYTHON:-} python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 11) else 1)'; then
      PY="$candidate"; break
    fi
  done
  if [ -z "$PY" ]; then
    echo "Python 3.11 is required. macOS: brew install python@3.11   Other: https://www.python.org/downloads/"
    exit 1
  fi
  echo "[1/4] Creating the Python virtual environment..."
  "$PY" -m venv .venv
  .venv/bin/python -m pip install --upgrade pip >/dev/null
  echo "      Installing Python packages (first run only, a few minutes)..."
  .venv/bin/python -m pip install -r backend/requirements.txt
fi

if [ ! -f models/all-MiniLM-L6-v2/model.safetensors ]; then
  echo "[2/4] Downloading the language model (about 90 MB, first run only)..."
  (cd backend && ../.venv/bin/python -m app.download_model)
fi

if [ ! -f frontend/dist/index.html ]; then
  command -v npm >/dev/null 2>&1 || { echo "Node.js 18 or later is required to build the frontend: https://nodejs.org"; exit 1; }
  echo "[3/4] Building the frontend (first run only)..."
  (cd frontend && npm install --no-audit --no-fund && npm run build)
fi

if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
fi

if [ ! -f data/hiretrack.db ]; then
  echo "[4/4] Creating and seeding the database (first run only)..."
  .venv/bin/python seed/seed_database.py
fi

if command -v lsof >/dev/null 2>&1 && lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port $PORT is already in use. Stop the other program, or run:  PORT=8001 ./start.sh"
  exit 1
fi

export HF_HUB_OFFLINE=1
echo
echo "HireTrack is starting on http://127.0.0.1:$PORT  (press Ctrl+C to stop)"
echo "Sign in as admin@hiretrack.local / Admin@123  (see INSTALLATION_GUIDE.md for all accounts)"
[ -n "${HT_NO_BROWSER:-}" ] || ( sleep 4; (command -v open >/dev/null && open "http://127.0.0.1:$PORT") || (command -v xdg-open >/dev/null && xdg-open "http://127.0.0.1:$PORT") || true ) >/dev/null 2>&1 &
cd backend
exec ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT"
