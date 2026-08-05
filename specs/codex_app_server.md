# Codex App Server contract

Codex owns authentication, thread state, execution, approvals, sandbox policy, and usage events. The app owns presentation and local organization. A conversation stores the exact upstream thread/session identifier required to resume; transcript text is not a substitute.

For the MVP, `backend/app/codex_client.py` starts `codex app-server` inside its own container with direct argument invocation. Docker pins CLI `0.145.0`. The client initializes, correlates JSONL request IDs, retains and resolves server requests, automatically answers `currentTime/read`, broadcasts notifications, drains stderr in bounded chunks, enforces a configurable 32 MiB protocol-line cap, and clears pending requests on resolution/stop. The process has the container toolchain, mounted Codex state, and the configured identical-path workspace mount; it does not inherit arbitrary host programs.

Compose sets `CODEX_HOME=/home/codex/.codex` and bind-mounts the invoking host user's `${HOME}/.codex` there. Bootstrap creates that source directory and verifies it is writable. A file-backed host login is reused; otherwise the operator can run `docker compose exec web codex login --device-auth` and restart the service. Authentication remains Codex-owned and persistent state remains outside the image.

The adapter initializes, lists threads using `sortKey: recency_at` plus optional `searchTerm`, starts/reads/resumes/names/archives/forks threads, starts/steers/interrupts turns, handles supported approval requests, and reads account/model/usage data. The frontend normalizes known history and streaming delta envelopes. Unknown interactive server requests remain pending and are shown as unsupported so the user can reject them safely. A response is reflected as resolved only after the backend POST succeeds; failure keeps the request actionable and retryable.

Threads are listed/read directly from Codex and locally enriched by authoritative thread ID; the app does not silently replace a missing or incompatible thread. Authentication files and raw environment values are not returned to the browser. App Server stderr is drained without retaining content; local system status intentionally exposes the configured workspace root to the single-operator UI.

## Gaps

- Confirm every method/event against pinned `0.145.0`; startup initializes but does not enforce a declared compatibility range.
- Add redacted fixtures for create, resume, approval, cancellation, usage, and process loss.
- Compatibility of older locally stored threads depends on supported upstream list/read/resume APIs.
