#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
IMAGE=${CODEX_WEBUI_IMAGE:-localhost/codex-webui-2:local}
PORT=${CODEX_WEBUI_PORT:-8766}
WORKSPACE_ROOT=${CODEX_WEBUI_WORKSPACE_ROOT:-$(dirname -- "$ROOT")}
CODEX_STATE=${CODEX_WEBUI_CODEX_STATE:-"$HOME/.codex"}
JEV_KEY_FILE=${CODEX_WEBUI_JEV_KEY_FILE:-"$ROOT/../jev-pipelines/.env"}
WORKSPACE_ROOT=$(realpath -- "$WORKSPACE_ROOT")
if [ ! -d "$CODEX_STATE" ]; then
  printf '%s\n' 'Codex state directory is missing. Sign in with the standalone CLI first.' >&2
  exit 1
fi
CODEX_STATE=$(realpath -- "$CODEX_STATE")
DETACH=false
TAILSCALE=false
BROWSER=false
for option in "$@"; do
  case "$option" in
    --detach) DETACH=true ;;
    --tailscale) TAILSCALE=true ;;
    --browser) BROWSER=true ;;
    *) printf '%s\n' 'Usage: tools/run-container.sh [--detach] [--tailscale] [--browser]' >&2; exit 1 ;;
  esac
done
ALLOWED_HOSTS=127.0.0.1,localhost
ALLOWED_ORIGINS="http://127.0.0.1:$PORT,http://localhost:$PORT"
if [ "$TAILSCALE" = true ]; then
  TAILSCALE_HOST=$(tailscale status --json | python3 -c '
import json, sys
status = json.load(sys.stdin)
host = (status.get("Self", {}).get("DNSName") or "").rstrip(".")
if status.get("BackendState") != "Running" or not host.endswith(".ts.net"):
    sys.exit("Connect Tailscale with a canonical .ts.net hostname first.")
print(host)
')
  ALLOWED_HOSTS="$ALLOWED_HOSTS,$TAILSCALE_HOST"
  ALLOWED_ORIGINS="$ALLOWED_ORIGINS,https://$TAILSCALE_HOST"
fi
set -- --rm --name "${CODEX_WEBUI_CONTAINER_NAME:-codex-webui-2}" --label app=codex-webui-2 \
  --userns=keep-id --user "$(id -u):$(id -g)" --cap-drop=ALL --security-opt=no-new-privileges \
  --publish "127.0.0.1:$PORT:8000" \
  --volume "$WORKSPACE_ROOT:$WORKSPACE_ROOT:rw" --volume "$CODEX_STATE:/codex:rw" \
  --volume "${CODEX_WEBUI_DATA_VOLUME:-codex-webui-2-data}:/data" \
  --env "CODEX_WEBUI_WORKSPACE_ROOT=$WORKSPACE_ROOT" \
  --env "CODEX_WEBUI_CODEX_STATE_SOURCE_DIR=$CODEX_STATE" \
  --env "CODEX_WEBUI_ALLOWED_HOSTS=$ALLOWED_HOSTS" \
  --env "CODEX_WEBUI_ALLOWED_ORIGINS=$ALLOWED_ORIGINS" \
  --env "CODEX_WEBUI_REALTIME_FEATURE_ENABLED=${CODEX_WEBUI_REALTIME_FEATURE_ENABLED:-true}"
if [ "$BROWSER" = true ]; then
  BRIDGE_DIRECTORY=${CODEX_WEBUI_BROWSER_BRIDGE_DIR:-"${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/codex-webui-browser"}
  [ -S "$BRIDGE_DIRECTORY/bridge.sock" ] || { printf '%s\n' 'Start the restricted host browser bridge first.' >&2; exit 1; }
  set -- "$@" --volume "$BRIDGE_DIRECTORY:/run/browser-bridge:ro" \
    --env CODEX_WEBUI_BROWSER_BRIDGE_SOCKET=/run/browser-bridge/bridge.sock
fi
if [ -f "$JEV_KEY_FILE" ]; then
  JEV_KEY_FILE=$(realpath -- "$JEV_KEY_FILE")
  set -- "$@" --volume "$JEV_KEY_FILE:/run/secrets/jev.env:ro" \
    --env CODEX_WEBUI_JEV_KEY_FILE=/run/secrets/jev.env \
    --env "CODEX_WEBUI_JEV_KEY_SOURCE_FILE=$JEV_KEY_FILE"
fi
if [ "$DETACH" = true ]; then
  set -- "$@" --detach
fi
printf 'Codex WebUI 2: http://127.0.0.1:%s\n' "$PORT"
if [ "$TAILSCALE" = true ]; then
  printf 'Private Tailscale URL: https://%s (requires Tailscale Serve)\n' "$TAILSCALE_HOST"
fi
exec podman run "$@" "$IMAGE"
