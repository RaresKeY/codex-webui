#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
IMAGE=${CODEX_WEBUI_IMAGE:-localhost/codex-webui-2:local}
CODEX_EXECUTABLE=${CODEX_BIN:-$(command -v codex || true)}
if [ -z "$CODEX_EXECUTABLE" ]; then
  printf '%s\n' 'The installed standalone Codex executable is required.' >&2
  exit 1
fi
CODEX_RUNTIME=$(dirname -- "$(readlink -f -- "$CODEX_EXECUTABLE")")
if [ ! -x "$CODEX_RUNTIME/codex-code-mode-host" ]; then
  printf '%s\n' 'Use the standalone Codex release, including codex-code-mode-host.' >&2
  exit 1
fi
podman build -f "$ROOT/Containerfile.tools" -t localhost/codex-webui-2-tools:local "$ROOT"
python3 "$ROOT/tools/frontend.py" check "$@"
podman build --format=docker -f "$ROOT/Containerfile" --build-context "codex-runtime=$CODEX_RUNTIME" \
  --build-arg "PUID=$(id -u)" --build-arg "PGID=$(id -g)" -t "$IMAGE" "$ROOT"
# Validate backend behavior using the resulting image without network or credentials.
podman run --rm --network=none --userns=keep-id --user "$(id -u):$(id -g)" \
  --cap-drop=ALL --security-opt=no-new-privileges --read-only --tmpfs /tmp:rw \
  --volume "$ROOT/backend:/checks:ro" --entrypoint python "$IMAGE" \
  -m pytest /checks/tests -q -p no:cacheprovider
