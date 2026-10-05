# Architecture

FastAPI/Python owns SQLite organization, bounded workspace access, the App Server stdio process, schedules and `task_router.py`. React/TypeScript owns normalized HTTP/WebSocket data, transcript presentation and per-conversation send state. The original app's data schema is unchanged; this new project uses separate app data and can mount the existing external Codex state.

`frontend/src/api.ts::sendPrompt` calls `/threads/{id}/route`, awaits its strictly validated choice, calls `/resume` with the selected model, awaits acknowledgement, then calls `/turns` with the exact ask and selected model/effort. Routing performs no Codex execution. Only `turn/start` begins a text task. Jev is server-side and has no browser credential or arbitrary provider URL surface.

`Containerfile.tools` provides pinned Deno/Python tooling. `tools/frontend.py` installs integrity-checked locked tarballs in a non-root container and executes build/lint/tests offline with scoped permissions. `Containerfile` packages the checked frontend, locked Python dependencies and standalone Rust Codex binaries. `tools/run-container.sh` owns loopback startup and external mounts.

## Gaps

- Reconnect still hydrates authoritative history rather than replaying missed events.
- No persisted routing evidence or automatic retry ledger is added; the UI never retries automatically.
- Runtime image architecture follows the supplied standalone Codex binary; amd64 is the current workstation target.
