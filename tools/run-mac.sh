#!/usr/bin/env sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PROJECT_PARENT=$(dirname -- "$PROJECT_ROOT")
MAC_HOST=${CODEX_WEBUI_HOST:-127.0.0.1}
MAC_PORT=${CODEX_WEBUI_PORT:-8765}
MAC_WORKSPACE_ROOT=${CODEX_WEBUI_WORKSPACE_ROOT:-$PROJECT_PARENT}
MAC_DATA_DIR=${CODEX_WEBUI_DATA_DIR:-"$HOME/Library/Application Support/Codex WebUI"}
PYTHON_EXECUTABLE=${PYTHON_BIN:-$(command -v python3 || true)}
if [ -n "${CODEX_BIN:-}" ]; then
  CODEX_EXECUTABLE=$CODEX_BIN
elif [ -x "$HOME/.local/bin/codex" ]; then
  # This is the documented standalone installer location. Prefer it over a
  # potentially older copy bundled inside another desktop application.
  CODEX_EXECUTABLE="$HOME/.local/bin/codex"
else
  CODEX_EXECUTABLE=$(command -v codex || true)
fi

if [ "$(uname -s)" != "Darwin" ]; then
  printf '%s\n' 'tools/run-mac.sh supports macOS. Use the container flow on Linux.' >&2
  exit 1
fi
if [ "$MAC_HOST" != "127.0.0.1" ] && [ "$MAC_HOST" != "localhost" ] && [ "$MAC_HOST" != "::1" ]; then
  printf '%s\n' 'The Mac companion only binds to a loopback host.' >&2
  exit 1
fi
if [ -z "$PYTHON_EXECUTABLE" ] || [ ! -x "$PYTHON_EXECUTABLE" ]; then
  printf '%s\n' 'Python 3 was not found.' >&2
  exit 1
fi
if [ -z "$CODEX_EXECUTABLE" ] || [ ! -x "$CODEX_EXECUTABLE" ]; then
  printf '%s\n' 'Codex CLI was not found. Install it and sign in with `codex login` first.' >&2
  exit 1
fi
if [ ! -d "$MAC_WORKSPACE_ROOT" ]; then
  printf 'Workspace root does not exist: %s\n' "$MAC_WORKSPACE_ROOT" >&2
  exit 1
fi

if [ ! -x "$PROJECT_ROOT/.venv/bin/python" ]; then
  "$PYTHON_EXECUTABLE" -m venv "$PROJECT_ROOT/.venv"
fi
"$PROJECT_ROOT/.venv/bin/python" -m pip install --disable-pip-version-check --quiet -r "$PROJECT_ROOT/backend/requirements.txt"

if command -v npm >/dev/null 2>&1; then
  npm --prefix "$PROJECT_ROOT/frontend" ci
  npm --prefix "$PROJECT_ROOT/frontend" run build
elif command -v pnpm >/dev/null 2>&1 && command -v node >/dev/null 2>&1; then
  pnpm --dir "$PROJECT_ROOT/frontend" install --lockfile=false
  pnpm --dir "$PROJECT_ROOT/frontend" run build
elif [ ! -f "$PROJECT_ROOT/frontend/dist/index.html" ]; then
  printf '%s\n' 'Node.js with npm or pnpm is required for the first frontend build (for example: `brew install node`).' >&2
  exit 1
fi

mkdir -p "$MAC_DATA_DIR"
export CODEX_WEBUI_CODEX_COMMAND="$CODEX_EXECUTABLE app-server"
export CODEX_WEBUI_DATA_DIR="$MAC_DATA_DIR"
export CODEX_WEBUI_WORKSPACE_ROOT="$MAC_WORKSPACE_ROOT"
export CODEX_WEBUI_FRONTEND_DIST="$PROJECT_ROOT/frontend/dist"
export CODEX_WEBUI_ALLOWED_HOSTS="127.0.0.1,localhost,[::1]"
export CODEX_WEBUI_ALLOWED_ORIGINS="http://127.0.0.1:$MAC_PORT,http://localhost:$MAC_PORT"
export CODEX_WEBUI_EXPERIMENTAL_API=true
export CODEX_WEBUI_REALTIME_FEATURE_ENABLED="${CODEX_WEBUI_REALTIME_FEATURE_ENABLED:-true}"
export CODEX_WEBUI_RUNTIME=localhost-companion

if [ "${CODEX_WEBUI_OPEN_BROWSER:-1}" = "1" ]; then
  (
    attempt=0
    while [ "$attempt" -lt 60 ]; do
      if /usr/bin/curl --fail --silent "http://127.0.0.1:$MAC_PORT/api/health" >/dev/null 2>&1; then
        /usr/bin/open "http://127.0.0.1:$MAC_PORT"
        exit 0
      fi
      attempt=$((attempt + 1))
      sleep 0.25
    done
  ) &
fi

cd "$PROJECT_ROOT"
exec "$PROJECT_ROOT/.venv/bin/python" -m uvicorn backend.app.main:app --host "$MAC_HOST" --port "$MAC_PORT"
