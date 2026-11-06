#!/usr/bin/env bash
# HireTrack one-command start for macOS (and Linux).
#   chmod +x start-mac.sh && ./start-mac.sh
# First run: creates the virtual environment, installs everything, downloads
# the model, builds the frontend and asks for an admin passcode.
# Later runs: just starts the app on http://127.0.0.1:8000
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
  PY=""
  for candidate in python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 11) else 1)'; then
      PY="$candidate"; break
    fi
  done
  if [ -z "$PY" ]; then
    echo "Python 3.11 is required (brew install python@3.11, or https://www.python.org/downloads/)."; exit 1
  fi
  echo "Creating virtual environment..."
  "$PY" -m venv .venv
  .venv/bin/python -m pip install --upgrade pip >/dev/null
  echo "Installing Python packages (first run only, a few minutes)..."
  .venv/bin/python -m pip install -r backend/requirements.txt
fi

if [ ! -f models/all-MiniLM-L6-v2/model.safetensors ]; then
  echo "Downloading the language model (about 90 MB, first run only)..."
  (cd backend && ../.venv/bin/python -m app.download_model)
fi

if [ ! -f frontend/dist/index.html ]; then
  command -v npm >/dev/null 2>&1 || { echo "Node.js 18+ is required to build the frontend: https://nodejs.org"; exit 1; }
  echo "Building the frontend (first run only)..."
  (cd frontend && npm install && npm run build)
fi

if [ ! -f .env ]; then
  echo
  read -r -s -p "Choose an admin passcode (6+ characters): " PASSCODE; echo
  (cd backend && ../.venv/bin/python -m app.hash_passcode "$PASSCODE" --write)
fi

export HF_HUB_OFFLINE=1
echo
echo "HireTrack is starting on http://127.0.0.1:8000  (press Ctrl+C to stop)"
( sleep 3; (command -v open >/dev/null && open http://127.0.0.1:8000) || (command -v xdg-open >/dev/null && xdg-open http://127.0.0.1:8000) || true ) &
cd backend
exec ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
