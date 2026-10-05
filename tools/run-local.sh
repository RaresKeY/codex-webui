#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PORT=${CODEX_WEBUI_PORT:-8766}
PYTHON_EXECUTABLE=${PYTHON_BIN:-"$ROOT/.venv/bin/python"}
if [ ! -x "$PYTHON_EXECUTABLE" ]; then
  printf '%s\n' 'Create .venv and install backend/requirements.txt first. See README.md.' >&2
  exit 1
fi
if [ ! -f "$ROOT/frontend/dist/index.html" ]; then
  python3 "$ROOT/tools/frontend.py" build
fi
export CODEX_WEBUI_DATA_DIR=${CODEX_WEBUI_DATA_DIR:-"$ROOT/data"}
export CODEX_WEBUI_FRONTEND_DIST="$ROOT/frontend/dist"
export CODEX_WEBUI_WORKSPACE_ROOT=${CODEX_WEBUI_WORKSPACE_ROOT:-"$(dirname -- "$ROOT")"}
export CODEX_WEBUI_ALLOWED_ORIGINS="http://127.0.0.1:$PORT,http://localhost:$PORT"
export CODEX_WEBUI_REALTIME_FEATURE_ENABLED=${CODEX_WEBUI_REALTIME_FEATURE_ENABLED:-true}
if [ -z "${CODEX_WEBUI_JEV_KEY_FILE:-}" ] && [ -f "$ROOT/../jev-pipelines/.env" ]; then
  export CODEX_WEBUI_JEV_KEY_FILE="$ROOT/../jev-pipelines/.env"
fi
cd "$ROOT/backend"
exec "$PYTHON_EXECUTABLE" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" --no-access-log
