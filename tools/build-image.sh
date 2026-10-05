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
# Coordinate builds with the workstation's label-scoped periodic cleanup.
exec 9>"${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman-build-retention.lock"
flock --shared 9

podman build --label io.rareskey.retention=retain --label io.rareskey.project=codex-webui-2 --label io.rareskey.purpose=toolchain --layer-label io.rareskey.retention=ephemeral --layer-label io.rareskey.project=codex-webui-2 -f "$ROOT/Containerfile.tools" -t localhost/codex-webui-2-tools:local "$ROOT"
python3 "$ROOT/tools/frontend.py" check "$@"
podman build --label io.rareskey.retention=retain --label io.rareskey.project=codex-webui-2 --label io.rareskey.purpose=runtime --layer-label io.rareskey.retention=ephemeral --layer-label io.rareskey.project=codex-webui-2 --format=docker -f "$ROOT/Containerfile" --build-context "codex-runtime=$CODEX_RUNTIME" \
  --build-arg "PUID=$(id -u)" --build-arg "PGID=$(id -g)" -t "$IMAGE" "$ROOT"
# Validate backend behavior using the resulting image without network or credentials.
podman run --rm --network=none --userns=keep-id --user "$(id -u):$(id -g)" \
  --cap-drop=ALL --security-opt=no-new-privileges --read-only --tmpfs /tmp:rw \
  --volume "$ROOT/backend:/checks:ro" --entrypoint python "$IMAGE" \
  -m pytest /checks/tests -q -p no:cacheprovider
# Exercise the actual standalone binary, not only mocked protocol responses.
podman run --rm --network=none --userns=keep-id --user "$(id -u):$(id -g)" \
  --cap-drop=ALL --security-opt=no-new-privileges --read-only --tmpfs /tmp:rw \
  --volume "$ROOT/tools:/checks/tools:ro" \
  --entrypoint python "$IMAGE" /checks/tools/check_thread_lifecycle.py

# Assert final ownership/retention rather than relying on inherited base labels.
for retained_image in "$IMAGE" localhost/codex-webui-2-tools:local; do
  podman image inspect "$retained_image" --format '{{json .Labels}}' | python3 -c 'import json,sys; labels=json.load(sys.stdin); assert labels.get("io.rareskey.retention")=="retain" and labels.get("io.rareskey.project")=="codex-webui-2" and labels.get("io.rareskey.purpose") in ("runtime","toolchain")'
done
