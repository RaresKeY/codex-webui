#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

python -m pytest "$ROOT/backend/tests"
npm --prefix "$ROOT/frontend" ci
npm --prefix "$ROOT/frontend" run build
npm --prefix "$ROOT/frontend" run lint
npm --prefix "$ROOT/frontend" test
