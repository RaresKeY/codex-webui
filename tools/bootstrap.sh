#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PARENT=$(dirname -- "$ROOT")
if [ "$(id -u)" = "0" ]; then
  printf '%s\n' 'Refusing to bootstrap as root. Run as the non-root user who owns the Codex state and workspaces.' >&2
  exit 1
fi

if [ "$(basename -- "$PARENT")" = "RawProjects" ]; then
  DEFAULT_WORKSPACES=$PARENT
else
  DEFAULT_WORKSPACES=$ROOT/workspaces
fi

CONFIGURED_WORKSPACES=
CONFIGURED_UID=
CONFIGURED_GID=
CONFIGURED_IMAGE=
if [ -f "$ROOT/.env" ]; then
  CONFIGURED_WORKSPACES=$(sed -n 's/^CODEX_WORKSPACES=//p' "$ROOT/.env" | tail -n 1)
  CONFIGURED_UID=$(sed -n 's/^PUID=//p' "$ROOT/.env" | tail -n 1)
  CONFIGURED_GID=$(sed -n 's/^PGID=//p' "$ROOT/.env" | tail -n 1)
  CONFIGURED_IMAGE=$(sed -n 's/^CODEX_WEBUI_IMAGE=//p' "$ROOT/.env" | tail -n 1)
fi
WORKSPACE_ROOT=${CODEX_WORKSPACES:-${CONFIGURED_WORKSPACES:-$DEFAULT_WORKSPACES}}
case "$WORKSPACE_ROOT" in
  /*) ;;
  *) WORKSPACE_ROOT=$(realpath -m -- "$ROOT/$WORKSPACE_ROOT") ;;
esac

RUN_UID=${PUID:-$CONFIGURED_UID}
RUN_GID=${PGID:-$CONFIGURED_GID}
RUN_UID=${RUN_UID:-$(id -u)}
RUN_GID=${RUN_GID:-$(id -g)}
if [ "$RUN_UID" = "0" ] || [ "$RUN_GID" = "0" ]; then
  printf '%s\n' 'Refusing to configure a root container. Run as the target user or set non-root PUID/PGID.' >&2
  exit 1
fi

mkdir -p "$ROOT/data/home" "$WORKSPACE_ROOT" "$HOME/.codex"
if [ ! -w "$HOME/.codex" ]; then
  printf '%s\n' "Codex state directory is not writable: $HOME/.codex" >&2
  printf '%s\n' 'Fix its ownership for this non-root user before starting the container.' >&2
  exit 1
fi
NEW_ENV=0
if [ ! -f "$ROOT/.env" ]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  NEW_ENV=1
  sed -i "s/^PUID=.*/PUID=$RUN_UID/" "$ROOT/.env"
  sed -i "s/^PGID=.*/PGID=$RUN_GID/" "$ROOT/.env"
fi
SAFE_WORKSPACE_ROOT=$(printf '%s' "$WORKSPACE_ROOT" | sed 's/[&|]/\\&/g')
if [ "$NEW_ENV" = "1" ] || [ -n "$CONFIGURED_WORKSPACES" ]; then
  sed -i "s|^CODEX_WORKSPACES=.*|CODEX_WORKSPACES=$SAFE_WORKSPACE_ROOT|" "$ROOT/.env"
else
  printf '\nCODEX_WORKSPACES=%s\n' "$WORKSPACE_ROOT" >> "$ROOT/.env"
fi

IMAGE_NAME=${CODEX_WEBUI_IMAGE:-${CONFIGURED_IMAGE:-codex-webui}}
if [ "$IMAGE_NAME" = "codex-webui" ]; then
  docker compose --project-directory "$ROOT" up --detach --build
else
  docker compose --project-directory "$ROOT" pull web
  docker compose --project-directory "$ROOT" up --detach --no-build --remove-orphans web
fi
docker compose --project-directory "$ROOT" ps

printf '\nCodex Web UI: http://127.0.0.1:%s\n' "${CODEX_WEBUI_PORT:-8765}"
