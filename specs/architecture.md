# Architecture

FastAPI/Python owns SQLite organization, bounded workspace access, the App Server stdio process, schedules, `task_router.py` and `chat_service.py`. React/TypeScript owns normalized HTTP/WebSocket data, transcript presentation and per-conversation send state. The original app's data schema is unchanged; this new project uses separate app data and can mount the existing external Codex state.

`frontend/src/api.ts::sendPrompt` submits exact input once to `/threads/{id}/messages` and consumes streamed progress/result. `chat_service.py` owns Jev selection, native thread loading, acknowledged `thread/settings/update` and subsequent `turn/start` with server-selected model/effort. `/turns` projects the same operation, accepts no caller model/effort, and cannot bypass routing. Thread creation accepts no prompt; direct steering is rejected. Routing performs no Codex execution. Only the acknowledged send operation starts an interactive text task. Jev is server-side and has no browser credential or arbitrary provider URL surface. Schedules and realtime voice retain their documented separate paths.

`Containerfile.tools` provides pinned Deno/Python tooling. `tools/frontend.py` installs integrity-checked locked tarballs in a non-root container and executes build/lint/tests offline with scoped permissions. `Containerfile` packages the checked frontend, locked Python dependencies and standalone Rust Codex binaries. `tools/run-container.sh` owns loopback startup and external mounts.

Bootstrap serves local shell data without native RPCs; history/models/usage hydrate independently, with images/workspace files deferred to their surfaces. `plugins.py` resolves explicit composer selections against native installed metadata before Jev and appends validated mentions after the exact ask. Native requests and browser reads have deadlines and do not retry execution. See `chat_interactions.md` for the presentation and failure contracts.

## Gaps

- Reconnect still hydrates authoritative history rather than replaying missed events.
- No persisted routing evidence or automatic retry ledger is added; the UI never retries automatically.
- Runtime image architecture follows the supplied standalone Codex binary; amd64 is the current workstation target.
