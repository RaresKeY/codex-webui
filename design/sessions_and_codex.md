# Sessions and Codex integration design

Resume always uses Codex's durable thread/session identity. Local events reconstruct display state but never substitute for native continuation. Imported sessions retain upstream identity and can be organized without rewriting history.

The adapter should discover capabilities and keep a tested compatibility table. Run presentation preserves event order, approval/input states, cancellation, interruption, reconnect, and upstream usage provenance. Current approval cards show action/scope, disable while sending, resolve only after backend acceptance, and remain pending with a retry path on failure; future input types should preserve the same lifecycle invariant.

## External host App Server

The desired host-toolchain mode runs Codex/App Server as the selected host user and connects from the container through either a permissioned Unix socket bind mount or a loopback-only WebSocket/TCP bridge. Authentication uses a per-install high-entropy token or mutually authenticated local channel. The protocol is typed and limited to App Server operations; it never accepts arbitrary shell command construction.

The runner validates origin/client identity, caps messages/concurrency, redacts logs, exposes a version/capability handshake, and scopes workspace roots. Unix socket ownership/mode should align with the container UID/GID. A loopback bridge needs replay-resistant authentication and must not bind publicly. The UI shows whether a session uses container or host execution because available tools and risk differ.

## Gaps

- Validate current App Server thread/list/resume/approval/cancel/usage behavior against a pinned Codex release.
- Choose Unix socket versus loopback WebSocket, token lifecycle, runner packaging, reconnect, and compromise recovery.
- Decide event replay limits and recovery across incompatible Codex updates.
