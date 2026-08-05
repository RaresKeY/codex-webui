#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

git -C "$ROOT" pull --ff-only origin main
CONFIGURED_IMAGE=
if [ -f "$ROOT/.env" ]; then
  CONFIGURED_IMAGE=$(sed -n 's/^CODEX_WEBUI_IMAGE=//p' "$ROOT/.env" | tail -n 1)
fi
IMAGE_NAME=${CODEX_WEBUI_IMAGE:-${CONFIGURED_IMAGE:-codex-webui}}
if [ "$IMAGE_NAME" = "codex-webui" ]; then
  docker compose --project-directory "$ROOT" build --pull
  docker compose --project-directory "$ROOT" up --detach --remove-orphans
else
  docker compose --project-directory "$ROOT" pull web
  docker compose --project-directory "$ROOT" up --detach --no-build --remove-orphans web
fi
docker compose --project-directory "$ROOT" ps
