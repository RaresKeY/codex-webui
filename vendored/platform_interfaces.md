# Platform interfaces

Rootless Podman builds the local Deno tools and WebUI runtime images. Runtime state uses identical absolute-path workspace mounts, an external Codex state directory, a separate app-data volume and an external read-only Jev credential file. The current installed standalone release and built image target linux/amd64. No registry publication, host container socket, remote exposure or Drive sync is configured.

The browser uses same-origin HTTP/WebSocket and optional WebRTC. The companion exposes only the inherited bounded workspace and App Server adapter surfaces.

## Gaps

- linux/arm64 needs a matching standalone release and its own runtime check.
- Non-1000 UID/GID and target-Pi operation remain unverified.
