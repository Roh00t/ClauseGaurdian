#!/usr/bin/env bash
# ClauseGuard v2 startup script. Run from repo root: bash start.sh
set -e
cd "$(dirname "$0")"

echo "ClauseGuard v2 - Starting..."

# IMPORTANT: on this machine `python3` is Homebrew 3.14 (no packages installed)
# while the working interpreter is 3.13. Prefer 3.13; fall back to python3.
PY="$(command -v python3.13 || command -v python3)"
echo "Using interpreter: $PY ($($PY -V 2>&1))"

# Install deps if needed (idempotent).
"$PY" -m pip install -r requirements.txt --break-system-packages -q || true

mkdir -p data

echo "Open http://127.0.0.1:8000"
exec "$PY" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
