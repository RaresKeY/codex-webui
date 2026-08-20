# Deployment and operations

## Status

Implemented local Mac launcher plus optional Linux container baseline.

## Source Sync

- Mac launcher: `tools/run-mac.sh`.
- Validation/schema/live smoke: `tools/validate.sh`, `tools/generate-app-server-schema.sh`, and `tools/smoke_app_server.py`.
- Container path: `Dockerfile`, `docker-compose.yml`, `tools/bootstrap.sh`, and `.github/workflows/ci.yml`.

## Behavior

`tools/run-mac.sh` is the primary entrypoint. It requires macOS, refuses non-loopback binding, honors an explicit `CODEX_BIN`, otherwise prefers the official standalone `~/.local/bin/codex`, and then falls back to `codex` on `PATH`. It creates `.venv`, installs declared Python dependencies, builds the frontend with npm or pnpm, creates app-owned data under `~/Library/Application Support/Codex WebUI` by default, starts Uvicorn on `127.0.0.1:8765`, and opens the localhost URL in the macOS default external browser after health succeeds. Set `CODEX_WEBUI_OPEN_BROWSER=0` when the page will be opened manually or through Codex's in-app Browser. The default workspace root is the checkout's parent and can be narrowed with `CODEX_WEBUI_WORKSPACE_ROOT`.

The Mac runtime does not copy or mount credentials: it inherits the normal CLI environment and lets Codex resolve its own login. It defaults `CODEX_WEBUI_REALTIME_FEATURE_ENABLED=true`, which inserts the supported `--enable realtime_conversation` argument before `app-server` for this child process only; setting it false omits the override. CLI updates use the official standalone installer documented at `https://developers.openai.com/codex/cli`; the app never silently updates Codex or writes its configuration.

The optional Compose service still publishes container port 8000 on loopback, runs non-root, drops capabilities, mounts workspace/Codex state/app data, and uses the container toolchain. Existing AMD64/ARM64 image CI and publishing remain present pending a product decision about that distribution.

## Verification

Shell syntax checks cover launch/validation scripts. Backend tests run on the Mac's Python 3.9 using `eval-type-backport`; frontend build/lint/tests run with Node. Schema generation and the read-only realtime capability probe use the same resolved standalone executable as the launcher. The signed-in text/approval smoke is opt-in because it invokes a model and creates an ephemeral App Server thread.

## Gaps

- Add a macOS CI job and signed/notarized wrapper if distributing outside source checkouts.
- Decide whether the container's independently pinned CLI must track the Mac-tested protocol version or be retired.
- Container target-Pi hardware and release rollback evidence remain incomplete.
