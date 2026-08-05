# Deployment, updates, sync, and backup

The initial topology is the `web` Compose service on 64-bit Linux. It publishes container port 8000 as `127.0.0.1:8765` by default, builds/runs under non-root `PUID:PGID`, drops all capabilities, enables `no-new-privileges`, and bundles Codex `0.145.0`. It mounts `${HOME}/.codex`, absolute `${CODEX_WORKSPACES}` at the identical absolute target, and `./data` at `/data`; runtime `HOME` is writable `/data/home`. CI builds and smoke-tests native `amd64` plus QEMU-emulated `linux/arm64`, checking the non-root identity, writable home, bundled Codex version, and degraded HTTP service. This is cross-architecture evidence, not a target-Pi hardware qualification.

`tools/bootstrap.sh` refuses root, derives the invoking user's IDs, and chooses the `RawProjects` parent when the repository is directly under it; otherwise it chooses the repository's absolute `workspaces/` path. It writes the absolute choice to `.env`, creates required directories, and starts Compose. `tools/update.sh` fast-forwards `main`, rebuilds with pulls, and replaces the service.

Tailscale is host/proxy configuration, not an app dependency. Keep the direct port loopback-bound. The in-app update endpoint is only a gated command scaffold and is disabled by default; the supported update path is the explicit host-side `tools/update.sh` command.

Git is authoritative for code/docs. Google Drive is a convenience mirror and backup destination, not live SQLite, Codex-state, or workspace replication. Create a consistent backup archive first; record version, schema, timestamp, scope, and exclusions. Restore is an explicit tested operation.

## Gaps

- Confirm the `linux/arm64` image on the target Pi hardware; QEMU CI does not validate Pi kernel, storage, thermal, or sustained-load behavior.
- Drive sync/conflict handling and automated backup/restore are not app features yet.
- Add immutable release metadata, rollback automation, and target-hardware performance/thermal regression tests.
