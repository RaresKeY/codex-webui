# Security and trust boundaries

## Status

Implemented loopback single-user baseline with operator-authorized private Tailscale Serve access.

## Source Sync

- HTTP/WebSocket policy: `backend/app/main.py`.
- Workspace containment: `backend/app/workspace.py`.
- Subprocess/log boundary: `backend/app/codex_client.py`.
- Text-chat execution policy: `backend/app/chat_service.py`, request models and message routes.
- Loopback lifecycle: `tools/run-container.sh`.
- Private HTTPS proxy: host Tailscale Serve; opt-in canonical Host/origin settings in `tools/run-container.sh --tailscale`.
- Browser media ownership: `frontend/src/realtime.ts`.

## Behavior

Protected assets are Codex credentials/state, workspace code and secrets, conversations, microphone audio, artifacts, and the authority to run Codex as the signed-in container user. The companion inherits the user's Codex environment but never returns authentication files or raw environment values to the browser. Stderr is drained without retaining diagnostics that may contain sensitive content.

The container launcher publishes loopback only. Jev reads credentials only on the server from environment or an external read-only file; see jev_routing.md. FastAPI accepts configured trusted Hosts, exact-same-origin or allowlisted browser mutations, and allowlisted WebSocket origins. Responses set restrictive same-origin CSP, frame denial, MIME-sniffing prevention, no-referrer, and `Permissions-Policy: microphone=(self)`. The microphone control remains disabled until a read-only App Server feature/account/voice probe succeeds. Browser capture can begin only from that explicit enabled control, and all local tracks stop when voice ends, fails, or the thread changes. Authentication stays inside Codex: the companion does not read API keys, OAuth tokens, account identifiers, or desktop attestation material, and the browser receives only capability state.

Workspace file access stays below the configured canonical root and rejects traversal and symlink escape. The configured Jev key file, its original host mount path, Codex state and its original host mount directory are excluded from browser tree/read/write/image/change routes, including canonical symlink aliases. This restriction applies to configured credential paths, rather than claiming to classify every secret in arbitrary project files. Native Codex retains its existing execution authority. The Changes adapter first resolves a repository below that root, then invokes a fixed read-only Git status argument list with hooks and filesystem monitoring disabled, bounded output, and no caller-supplied flags. App Server requests use structured arguments, not shell construction. The contextual Terminal exposes only thread-scoped background-process metadata: no companion route projects App Server's generic shell, command, spawn, write-stdin, terminate, or resize methods. The companion itself does not write Codex configuration; realtime enablement is a child-process command-line override, and upstream App Server retains its documented policy/config behavior during normal user actions.

Anyone who reaches the loopback UI has the effective Codex authority of the signed-in container user. These controls prevent common cross-site drive-by use but are not authentication.

The operator may explicitly enable private remote access through Tailscale Serve. The container remains loopback-only and permits exactly the workstation's connected `.ts.net` hostname and HTTPS origin. HTTPS terminates in the host Tailscale daemon, and tailnet admission plus existing Tailscale access controls govern reachability. The companion does not interpret identity headers or implement separate user accounts; every admitted client has the same signed-in Codex authority. Funnel and public/LAN publication are outside this deployment. Existing mutation and WebSocket Origin rejection remains enforced through the proxy. This deployment does not add cookies or cookie-based authentication.

Interactive text execution is server-owned: both message URLs use a fresh Jev decision in Auto or an explicitly saved per-chat manual choice, and require actual model/effort settings acknowledgement before the exact ask reaches Codex. Caller model/effort overrides and thread-start prompts are rejected, and direct steering is disabled. Classification previews and public resume/model changes grant no execution shortcut; only the typed per-chat execution choice selects the manual path. Per-thread leases reject concurrent sends/model changes within this companion process. This contract applies to submitted text chat; scheduling and experimental realtime retain separate documented paths.

The experimental browser launches only audited restricted Chromium Flatpak with a dedicated profile, denied downloads, no host mounts/display sockets, and private CDP pipes. Browser observations are untrusted and bounded; password/file fields and input values are excluded. Only fixed observed-control actions are accepted, with stale-target checks; there is no user/model JavaScript endpoint. HTTPS navigation is a document gate, not a firewall: shared browser networking can still reach internal resources through subrequests or DNS. It does not inherit Codex sandbox/network policy. Direct human click/key/text/wheel input uses a separate same-origin route and private Unix bridge; coordinate input is excluded from the agent tool schema. Human input can focus embedded frames and password fields, while the observer still excludes passwords and field values. Typed input and cookies are never logged or exposed through cookie-export endpoints; cookies stay in the dedicated profile with the existing basic-store limitation. Actions rely on the agent following explicit user authority; Jev task effect allowlists are not ported. See [browser integration](browser_integration.md).

## Verification

The explicit per-chat permission control can select full access with automatic approval review or YOLO. The backend accepts only named presets, serializes changes against submissions, rejects active native turns and requires native acknowledgement before persisting the choice. Every text send rebinds the saved policy before execution. This changes Codex authority inside the existing runtime/mounts; it grants no administrator privileges and cannot override managed restrictions. See `chat_permissions.md` for the exact contract.

API tests cover trusted Host, Origin/fetch-site, WebSocket Origin, security headers, traversal, exact thread scoping, active-writer isolation, bounded Git status parsing in a real temporary repository, and direct-client routing bypasses. Routed-chat errors return bounded messages rather than provider/RPC diagnostics. The live smoke compares the selected Codex `config.toml` digest before/after and denies its command before execution.

## Gaps

- No app authentication, per-user authorization, rate limiting, or cookie-based remote CSRF design exists. Tailscale identity headers are not trusted or consumed by the app.
- Workspace resolution retains an ancestor-component TOCTOU gap under a hostile concurrent filesystem actor.
- Add hostile-content tests, dependency audit/SBOM, and browser permission UX evidence.
