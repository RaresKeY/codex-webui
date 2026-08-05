# Security and trust boundaries

Protected assets are Codex credentials/state, workspace code and secrets, conversations, artifacts, and the authority to run Codex. Threats include unauthorized browser use, cross-site requests, traversal/symlink escape, command injection, hostile rendered content, dependency compromise, and log leakage.

Implemented deployment controls are loopback publication, dynamic non-root PUID/PGID at build/runtime, writable `/data/home`, all-capability drop, `no-new-privileges`, no Docker socket, explicit identical-path workspace mount, subprocess argument arrays, and canonical workspace-root checks. FastAPI enforces configured trusted Hosts, configured or exact-same-origin state-changing browser requests, and WebSocket origins. Responses set a restrictive same-origin CSP (with inline styles currently allowed), deny framing, disable MIME sniffing, and set `Referrer-Policy: no-referrer`.

Authenticated Tailscale/proxy identity is not implemented, so remote exposure is outside the current supported boundary.

## Gaps

- There is no app authentication or rate limiting. Current origin/fetch-site protection is a loopback baseline, not authorization; cookie-based remote sessions would need an explicit CSRF-token design.
- Workspace resolution still has an ancestor-component read/write TOCTOU gap under a hostile concurrent filesystem actor.
- Add authenticated trusted-proxy/Tailscale identity, hostile-content tests, dependency/container audit, SBOM, and a private security contact.
