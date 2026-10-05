# Security and remote-access design

Loopback remains the container boundary. Operator-authorized private access now uses host Tailscale Serve and the canonical workstation Host/HTTPS origin, with tailnet admission and network access controls governing reachability; see `specs/security_trust.md`. The MVP restricts trusted Hosts/origins and supplies CSP/frame/nosniff/referrer headers, but has no application user authentication or rate limiting. Future per-user identity would come from verified Tailscale proxy headers or native app sessions/OIDC; headers must be trusted only from known hops. Cookie-authenticated writes would need explicit CSRF tokens regardless of tailnet privacy.

Container hardening includes non-root execution, read-only root where workable, capability drop, resource limits, narrow mounts, and no Docker socket. Workspace/model content is untrusted and sanitized. Destructive authority uses step-up confirmation and audit state.

The local companion runs with mounted-workspace Codex authority and therefore stays loopback-only, scopes workspace file APIs, owns App Server over private stdio, and exposes no generic command endpoint. A future remote transport would additionally need authenticated local transport, workspace allowlists, concurrency limits, and revocable credentials.

Experimental browser media must fail closed: feature availability, auth suitability, and voice discovery are verified before enabling capture. Desktop-private attestation or voice credentials are not reusable interfaces for the standalone client.

## Gaps

- Design per-user Tailscale identity enforcement or application sessions beyond the current shared-authority private network boundary.
- Define authenticated sessions, CSRF tokens, rate limiting, recovery, audit retention, stricter remote CSP/proxy policy, secrets, security updates, and perform review before remote publication.
- Review microphone permission, SDP handling, and WebRTC teardown with real browser evidence.
