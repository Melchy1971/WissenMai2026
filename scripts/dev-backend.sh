#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(dirname "$0")"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
VENV_PYTHON="$BACKEND_DIR/.venv/Scripts/python.exe"
LOCAL_DEV_DATABASE_URL="postgresql+psycopg://testuser:testpass@127.0.0.1:5433/wissen_test"
BOOTSTRAP_SCRIPT="$REPO_ROOT/scripts/bootstrap_local_backend.py"

if [ ! -f "$VENV_PYTHON" ]; then
  echo "Backend virtual environment not found at $VENV_PYTHON. Create it first." >&2
  exit 1
fi

export DATABASE_URL="${DATABASE_URL:-$LOCAL_DEV_DATABASE_URL}"

"$VENV_PYTHON" -c "import os, sys, psycopg; url=os.environ.get('DATABASE_URL');
if not url:
	raise SystemExit('DATABASE_URL is missing. Set DATABASE_URL or start the local dev database with scripts/dev-db.sh.')
try:
	conn = psycopg.connect(url.replace('postgresql+psycopg://', 'postgresql://', 1), connect_timeout=3)
	conn.close()
except Exception as exc:
	raise SystemExit(f'Cannot connect to DATABASE_URL={url}. Start the local dev database with scripts/dev-db.sh or set DATABASE_URL explicitly. Root cause: {exc}')"

"$VENV_PYTHON" "$BOOTSTRAP_SCRIPT"

cd "$BACKEND_DIR"
"$VENV_PYTHON" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
