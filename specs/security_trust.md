# Security and trust boundaries

## Status

Implemented loopback single-user baseline; no remote-access authorization.

## Source Sync

- HTTP/WebSocket policy: `backend/app/main.py`.
- Workspace containment: `backend/app/workspace.py`.
- Subprocess/log boundary: `backend/app/codex_client.py`.
- Loopback lifecycle: `tools/run-mac.sh`.
- Browser media ownership: `frontend/src/realtime.ts`.

## Behavior

Protected assets are Codex credentials/state, workspace code and secrets, conversations, microphone audio, artifacts, and the authority to run Codex as the Mac user. The companion inherits the user's Codex environment but never returns authentication files or raw environment values to the browser. Stderr is drained without retaining diagnostics that may contain sensitive content.

The Mac launcher refuses non-loopback hosts. FastAPI accepts configured trusted Hosts, exact-same-origin or allowlisted browser mutations, and allowlisted WebSocket origins. Responses set restrictive same-origin CSP, frame denial, MIME-sniffing prevention, no-referrer, and `Permissions-Policy: microphone=(self)`. The microphone control remains disabled until a read-only App Server feature/account/voice probe succeeds. Browser capture can begin only from that explicit enabled control, and all local tracks stop when voice ends, fails, or the thread changes. Authentication stays inside Codex: the companion does not read API keys, OAuth tokens, account identifiers, or desktop attestation material, and the browser receives only capability state.

Workspace file access stays below the configured canonical root and rejects traversal and symlink escape. The Changes adapter first resolves a repository below that root, then invokes a fixed read-only Git status argument list with hooks and filesystem monitoring disabled, bounded output, and no caller-supplied flags. App Server requests use structured arguments, not shell construction. The contextual Terminal exposes only thread-scoped background-process metadata: no companion route projects App Server's generic shell, command, spawn, write-stdin, terminate, or resize methods. The companion itself does not write Codex configuration; realtime enablement is a child-process command-line override, and upstream App Server retains its documented policy/config behavior during normal user actions.

Anyone who reaches the loopback UI has the effective Codex authority of the signed-in Mac user. These controls prevent common cross-site drive-by use but are not authentication.

## Verification

API tests cover trusted Host, Origin/fetch-site, WebSocket Origin, security headers, traversal, exact thread scoping, active-writer isolation, and bounded Git status parsing in a real temporary repository. The live smoke compares the selected Codex `config.toml` digest before/after and denies its command before execution.

## Gaps

- No app authentication, rate limiting, trusted proxy, or remote CSRF design exists.
- Workspace resolution retains an ancestor-component TOCTOU gap under a hostile concurrent filesystem actor.
- Add hostile-content tests, dependency audit/SBOM, and browser permission UX evidence.
