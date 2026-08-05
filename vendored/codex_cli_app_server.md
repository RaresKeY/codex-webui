# Codex CLI and App Server

Codex is an external runtime providing auth, threads, execution, approvals, sandbox policy, events, and usage. This repository owns only its adapter. The container currently pins Codex CLI `0.145.0`; startup should probe the actual executable and fail clearly on unsupported protocol combinations.

Primary references:

- [Codex repository](https://github.com/openai/codex)
- [Codex documentation](https://developers.openai.com/codex/)

Prefer supported App Server interfaces over private state-file parsing. Current integration uses kebab-case `on-request`/`workspace-write` REST settings and translates workspace-write turns to an App Server `sandboxPolicy` object with no extra writable roots and network disabled. It caps JSONL protocol lines at 32 MiB, automatically handles `currentTime/read`, and retains other server requests for UI resolution. Never expose authentication or assume undocumented layouts are stable. Future host-runner compatibility is negotiated independently from the web container version.

## Gaps

- Record executable invocation, protocol transport, capability matrix, and exact upstream source revision for used methods.
- Validate `linux/arm64`, thread discovery, and the future external transport.
