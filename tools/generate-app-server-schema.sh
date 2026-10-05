#!/usr/bin/env sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCHEMA_OUTPUT=${1:-"$PROJECT_ROOT/tmp/app-server-schema"}
CODEX_EXECUTABLE=${CODEX_BIN:-$(command -v codex || true)}

if [ -z "$CODEX_EXECUTABLE" ] || [ ! -x "$CODEX_EXECUTABLE" ]; then
  printf '%s\n' 'Codex CLI was not found. Set CODEX_BIN to the executable path.' >&2
  exit 1
fi

mkdir -p "$SCHEMA_OUTPUT/typescript" "$SCHEMA_OUTPUT/json"
"$CODEX_EXECUTABLE" app-server generate-ts --experimental --out "$SCHEMA_OUTPUT/typescript"
"$CODEX_EXECUTABLE" app-server generate-json-schema --experimental --out "$SCHEMA_OUTPUT/json"
"$CODEX_EXECUTABLE" --version > "$SCHEMA_OUTPUT/CODEX_VERSION"

printf 'Generated App Server schema in %s\n' "$SCHEMA_OUTPUT"
