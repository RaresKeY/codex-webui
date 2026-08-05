#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

git -C "$ROOT" pull --ff-only origin main
docker compose --project-directory "$ROOT" build --pull
docker compose --project-directory "$ROOT" up --detach --remove-orphans
docker compose --project-directory "$ROOT" ps

