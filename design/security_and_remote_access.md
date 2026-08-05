# Security and remote-access design

Loopback is first. The MVP already restricts trusted Hosts/origins and supplies CSP/frame/nosniff/referrer headers, but has no user authentication or rate limiting. Later, host Tailscale Serve or a hardened proxy forwards to the loopback container. Identity comes from verified Tailscale proxy headers or native app sessions/OIDC; headers are trusted only from known hops. Cookie-authenticated writes need explicit CSRF tokens regardless of tailnet privacy.

Container hardening includes non-root execution, read-only root where workable, capability drop, resource limits, narrow mounts, and no Docker socket. Workspace/model content is untrusted and sanitized. Destructive authority uses step-up confirmation and audit state.

An external host App Server transport expands authority beyond container tools. It therefore needs authenticated local transport, workspace allowlists, distinct UI disclosure, concurrency limits, revocable credentials, and no generic command endpoint.

## Gaps

- Choose and threat-model Tailscale identity plus host-runner authentication.
- Define authenticated sessions, CSRF tokens, rate limiting, recovery, audit retention, stricter remote CSP/proxy policy, secrets, security updates, and perform review before remote publication.
