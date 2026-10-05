#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_EXECUTABLE=${PYTHON_BIN:-"$ROOT/.venv/bin/python"}
"$PYTHON_EXECUTABLE" -m pytest "$ROOT/backend/tests" -q
python3 "$ROOT/tools/frontend.py" check
