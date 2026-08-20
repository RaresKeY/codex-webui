#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_EXECUTABLE=${PYTHON_BIN:-$(command -v python3 || command -v python || true)}

if [ -z "$PYTHON_EXECUTABLE" ]; then
  printf '%s\n' 'Python 3 was not found.' >&2
  exit 1
fi
"$PYTHON_EXECUTABLE" -m pytest "$ROOT/backend/tests"

if command -v npm >/dev/null 2>&1; then
  npm --prefix "$ROOT/frontend" ci
  npm --prefix "$ROOT/frontend" run build
  npm --prefix "$ROOT/frontend" run lint
  npm --prefix "$ROOT/frontend" test
elif command -v pnpm >/dev/null 2>&1; then
  pnpm --dir "$ROOT/frontend" install --lockfile=false
  pnpm --dir "$ROOT/frontend" run build
  pnpm --dir "$ROOT/frontend" run lint
  pnpm --dir "$ROOT/frontend" test
else
  printf '%s\n' 'Node.js package tooling was not found (npm or pnpm is required).' >&2
  exit 1
fi
