# Deployment, updates, sync, and backup

The initial topology is the `web` Compose service on 64-bit Linux. It publishes container port 8000 as `127.0.0.1:8765` by default, builds/runs under non-root `PUID:PGID`, drops all capabilities, enables `no-new-privileges`, and bundles Codex `0.145.0`. It mounts `${HOME}/.codex`, absolute `${CODEX_WORKSPACES}` at the identical absolute target, and `./data` at `/data`; runtime `HOME` is writable `/data/home`. CI builds and smoke-tests native `amd64` plus QEMU-emulated `linux/arm64`, checking the non-root identity, writable home, bundled Codex version, and degraded HTTP service. After every successful `main` CI run, a gated job rebuilds that commit and publishes a combined `linux/amd64` and `linux/arm64` manifest to `ghcr.io/rareskey/codex-webui` with `latest` and commit-derived `sha-...` tags. Ref-scoped concurrency cancels stale runs before an older commit can replace a newer `latest`. Publishing uses the workflow `GITHUB_TOKEN` with job-scoped `packages: write`; no long-lived registry secret is configured. This is cross-architecture evidence, not a target-Pi hardware qualification.

`tools/bootstrap.sh` refuses root, derives the invoking user's IDs, and chooses the `RawProjects` parent when the repository is directly under it; otherwise it chooses the repository's absolute `workspaces/` path. It writes the absolute choice to `.env`, creates the data/workspace/Codex-state directories, verifies that Codex state is writable, and starts Compose. The default `codex-webui` image is built locally; any configured non-default `CODEX_WEBUI_IMAGE` is pulled and started with builds disabled. `tools/update.sh` fast-forwards `main`, then applies the same local-build versus remote-pull selection before replacing the service. A prebuilt deployment selects `CODEX_WEBUI_IMAGE=ghcr.io/rareskey/codex-webui` and `CODEX_WEBUI_IMAGE_TAG=<tag>` in `.env`.

Codex credentials are never part of the image. The host user's `${HOME}/.codex` is mounted at `/home/codex/.codex`; a file-backed host login is reused. When login is absent or keyring-only, the supported operator action is `docker compose exec web codex login --device-auth`, followed by `docker compose restart web`. Device-auth state persists through the bind mount.

Tailscale is host/proxy configuration, not an app dependency. Keep the direct port loopback-bound. The in-app update endpoint is only a gated command scaffold and is disabled by default; the supported update path is the explicit host-side `tools/update.sh` command.

Git is authoritative for code/docs. Google Drive is a convenience mirror and backup destination, not live SQLite, Codex-state, or workspace replication. Create a consistent backup archive first; record version, schema, timestamp, scope, and exclusions. Restore is an explicit tested operation.

## Gaps

- Confirm the `linux/arm64` image on the target Pi hardware; QEMU CI does not validate Pi kernel, storage, thermal, or sustained-load behavior.
- Drive sync/conflict handling and automated backup/restore are not app features yet.
- Decide versioned release tags, digest selection, package retention, rollback automation, non-1000 runtime-identity support for prebuilt images, and target-hardware performance/thermal regression tests.
