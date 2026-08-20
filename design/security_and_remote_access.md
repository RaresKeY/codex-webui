# Security and remote-access design

Loopback is first. The MVP already restricts trusted Hosts/origins and supplies CSP/frame/nosniff/referrer headers, but has no user authentication or rate limiting. Later, host Tailscale Serve or a hardened proxy forwards to the loopback container. Identity comes from verified Tailscale proxy headers or native app sessions/OIDC; headers are trusted only from known hops. Cookie-authenticated writes need explicit CSRF tokens regardless of tailnet privacy.

Container hardening includes non-root execution, read-only root where workable, capability drop, resource limits, narrow mounts, and no Docker socket. Workspace/model content is untrusted and sanitized. Destructive authority uses step-up confirmation and audit state.

The Mac companion runs with host-user Codex authority and therefore stays loopback-only, scopes workspace file APIs, owns App Server over private stdio, and exposes no generic command endpoint. A future remote transport would additionally need authenticated local transport, workspace allowlists, concurrency limits, and revocable credentials.

Experimental browser media must fail closed: feature availability, auth suitability, and voice discovery are verified before enabling capture. Desktop-private attestation or voice credentials are not reusable interfaces for the standalone client.

## Gaps

- Choose and threat-model Tailscale identity plus host-runner authentication.
- Define authenticated sessions, CSRF tokens, rate limiting, recovery, audit retention, stricter remote CSP/proxy policy, secrets, security updates, and perform review before remote publication.
- Review microphone permission, SDP handling, and WebRTC teardown with real browser evidence.
