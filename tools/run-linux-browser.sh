#!/usr/bin/env sh
# Local experimental companion; never publishes or opens a desktop window.
set -eu
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BROWSER_PORT=${CODEX_WEBUI_PORT:-8765}
PYTHON_EXECUTABLE=${PYTHON_BIN:-"$PROJECT_ROOT/.venv/bin/python"}
CODEX_EXECUTABLE=${CODEX_BIN:-$(command -v codex || true)}
if [ "$(uname -s)" != "Linux" ]; then
  printf '%s\n' 'The experimental browser requires Linux.' >&2
  exit 1
fi
case "$BROWSER_PORT" in ''|*[!0-9]*) printf '%s\n' 'Port must be numeric.' >&2; exit 1;; esac
if [ -z "$CODEX_EXECUTABLE" ] || [ ! -x "$CODEX_EXECUTABLE" ] || [ ! -x "$PYTHON_EXECUTABLE" ]; then
  printf '%s\n' 'Install the declared backend requirements in .venv and provide the installed Codex CLI (PYTHON_BIN/CODEX_BIN can select existing runtimes).' >&2
  exit 1
fi
if [ ! -f "$PROJECT_ROOT/frontend/dist/index.html" ]; then
  printf '%s\n' 'Build the frontend with the project-pinned dependencies before launching.' >&2
  exit 1
fi
flatpak info --user io.github.ungoogled_software.ungoogled_chromium >/dev/null
export CODEX_WEBUI_RUNTIME=localhost-companion
export CODEX_WEBUI_BROWSER_ENABLED=true
export CODEX_WEBUI_CODEX_COMMAND="$CODEX_EXECUTABLE app-server"
export CODEX_WEBUI_DATA_DIR="${CODEX_WEBUI_DATA_DIR:-$HOME/.local/share/codex-webui-browser-experiment}"
export CODEX_WEBUI_WORKSPACE_ROOT="${CODEX_WEBUI_WORKSPACE_ROOT:-$PROJECT_ROOT}"
export CODEX_WEBUI_FRONTEND_DIST="$PROJECT_ROOT/frontend/dist"
export CODEX_WEBUI_ALLOWED_HOSTS="127.0.0.1,localhost,[::1]"
export CODEX_WEBUI_ALLOWED_ORIGINS="http://127.0.0.1:$BROWSER_PORT,http://localhost:$BROWSER_PORT"
cd "$PROJECT_ROOT"
printf 'Experimental browser companion: http://127.0.0.1:%s\n' "$BROWSER_PORT"
exec "$PYTHON_EXECUTABLE" -m uvicorn backend.app.main:app --host 127.0.0.1 --port "$BROWSER_PORT" --timeout-graceful-shutdown 5
