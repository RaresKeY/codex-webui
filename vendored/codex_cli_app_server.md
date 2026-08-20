# Codex CLI and App Server

Codex is the external runtime for authentication, threads, execution, approvals, sandbox policy, events, usage, and realtime. This repository owns only its localhost adapter and browser projection.

## Compatibility record

- Installed/tested executable: official standalone `codex-cli 0.147.0` at implementation time.
- Schema source: `codex app-server generate-ts --experimental` and `generate-json-schema --experimental` from that executable.
- Release source reference: `openai/codex` tag `rust-v0.147.0` (`be6e8eac029b183056b7e4402879f15d2c85f61b`).
- Additional local open-source reference: `openai/codex` commit `4861236f06d0df397436531b4aa3d7fa6975959c` (2026-08-15).
- Transport: one companion-owned stdio JSONL process; JSON-RPC 2.0 header omitted on the wire as documented.
- Internal owner: `backend/app/codex_client.py`.

Primary references:

- [Codex App Server README](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md)
- [Codex repository](https://github.com/openai/codex)
- [Official Codex CLI install/update documentation](https://developers.openai.com/codex/cli)

## Used protocol subset

Initialization is `initialize` then `initialized`, with `capabilities.experimentalApi: true` and `requestAttestation: false`. The client uses current v2 thread/turn methods, account/model/usage reads, the read-only `thread/backgroundTerminals/list` inventory, `currentTime/read`, command and file approval requests, and exact `accept`/`decline` decisions.

The generated ClientRequest union has no browser-tab, navigation, DOM, or screenshot method. Codex Desktop's in-app Browser therefore remains outside this standalone client's public integration boundary. The same union does contain generic shell/command/process and background-terminal mutation methods; the companion deliberately projects none of those, exposing only Codex-driven output notifications and read-only terminal metadata.

Realtime is experimental but public in the generated schema. The browser follows the upstream WebRTC example: audio track plus `oai-events` data channel before `createOffer()`, `thread/realtime/start` with the browser SDP, `thread/realtime/sdp` for the answer, and `thread/realtime/stop` for teardown. The client requests version `v3`; the upstream implementation accepts WebRTC v1/v3 and rejects v2. The stable CLI lists `realtime_conversation` as under development and off by default. The Mac launcher uses its supported process-scoped `--enable realtime_conversation` flag, then verifies effective feature state, required account presence, and voices. Stable source and a live no-session probe confirm that WebRTC v3 uses the existing ChatGPT auth provider; only the legacy direct WebSocket path has the API-key-only helper.

Required 0.147 sandbox-policy fields are preserved: read-only includes `networkAccess`; workspace-write includes `writableRoots`, `networkAccess`, `excludeTmpdirEnvVar`, and `excludeSlashTmp`.

The Mac companion inherits Codex environment/login resolution and never reads private auth layouts. It does not communicate with or patch the desktop app. The runtime feature argument does not persist configuration. `tools/smoke_app_server.py` uses an ephemeral read-only thread and a denied approval, then compares config digests.

## Gaps

- The optional Docker image still pins Codex `0.145.0`; realtime voice is a Mac-host 0.147 target until that path is upgraded and independently verified.
- There is no declared semantic compatibility range or automatic method negotiation beyond initialization opt-in.
- Re-run schema generation and adapter/live tests for every supported Codex CLI upgrade.
