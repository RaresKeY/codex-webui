#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_EXECUTABLE=${PYTHON_BIN:-"$ROOT/.venv/bin/python"}
BRIDGE_DIRECTORY=${CODEX_WEBUI_BROWSER_BRIDGE_DIR:-"${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/codex-webui-browser"}
[ "$(uname -s)" = Linux ]
flatpak info --user io.github.ungoogled_software.ungoogled_chromium >/dev/null
umask 077
mkdir -p "$BRIDGE_DIRECTORY"
chmod 700 "$BRIDGE_DIRECTORY"
cd "$ROOT"
exec "$PYTHON_EXECUTABLE" -m uvicorn backend.app.browser_bridge:app --uds "$BRIDGE_DIRECTORY/bridge.sock" --no-access-log --timeout-graceful-shutdown 5
