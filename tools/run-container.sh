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
DETACH=${1:-}
if [ -n "$DETACH" ] && [ "$DETACH" != "--detach" ]; then
  printf '%s\n' 'Usage: tools/run-container.sh [--detach]' >&2
  exit 1
fi
set -- --rm --name codex-webui-2 --label app=codex-webui-2 \
  --userns=keep-id --user "$(id -u):$(id -g)" --cap-drop=ALL --security-opt=no-new-privileges \
  --publish "127.0.0.1:$PORT:8000" \
  --volume "$WORKSPACE_ROOT:$WORKSPACE_ROOT:rw" --volume "$CODEX_STATE:/codex:rw" \
  --volume codex-webui-2-data:/data \
  --env "CODEX_WEBUI_WORKSPACE_ROOT=$WORKSPACE_ROOT" \
  --env "CODEX_WEBUI_ALLOWED_ORIGINS=http://127.0.0.1:$PORT,http://localhost:$PORT" \
  --env "CODEX_WEBUI_REALTIME_FEATURE_ENABLED=${CODEX_WEBUI_REALTIME_FEATURE_ENABLED:-true}"
if [ -f "$JEV_KEY_FILE" ]; then
  set -- "$@" --volume "$JEV_KEY_FILE:/run/secrets/jev.env:ro" --env CODEX_WEBUI_JEV_KEY_FILE=/run/secrets/jev.env
fi
if [ "$DETACH" = "--detach" ]; then
  set -- "$@" --detach
fi
printf 'Codex WebUI 2: http://127.0.0.1:%s\n' "$PORT"
exec podman run "$@" "$IMAGE"
