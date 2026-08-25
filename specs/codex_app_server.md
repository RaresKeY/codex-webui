# Codex App Server contract

## Status

Implemented Mac companion subset against official standalone `codex-cli 0.147.0`; optional container compatibility remains partial.

## Source Sync

- `backend/app/codex_client.py`: stdio ownership, initialization, correlation, server requests, subscriptions, and shutdown.
- `backend/app/main.py`: HTTP/WebSocket projection for threads, turns, approvals, and realtime.
- `backend/app/models.py` and `backend/app/config.py`: accepted client inputs and wire-policy conversion.
- `frontend/src/api.ts`, `frontend/src/realtime.ts`, and `frontend/src/app-server-protocol.ts`: event normalization, exact protocol subset, and browser WebRTC leg.
- `tools/generate-app-server-schema.sh` and `tools/smoke_app_server.py`: schema drift and opt-in live verification.

Any change to these protocol calls or payloads requires this spec, adapter tests, and the vendored compatibility note to change in the same turn.

## Behavior

Codex owns authentication, threads, turns, execution, approvals, sandbox policy, usage, and realtime sessions. The app owns presentation and local organization. A conversation stores and uses the upstream thread ID; transcript text never substitutes for native continuation.

The Mac companion directly launches the selected host `codex app-server` with inherited environment and stdio JSONL. It does not set a replacement `CODEX_HOME`, copy login files, parse private state, or communicate with the Codex desktop app. Initialization sends one `initialize` request followed by `initialized` and declares:

```json
{"experimentalApi": true, "requestAttestation": false}
```

The experimental opt-in is required by the public realtime methods. This client does not claim desktop attestation support. The adapter correlates numeric client request IDs, retains server-initiated requests, automatically answers `currentTime/read`, drains stderr without retaining it, caps protocol lines at 32 MiB, and clears requests on server resolution or disconnect.

The supported thread/turn surface is `thread/list`, `thread/read`, `thread/start`, `thread/resume`, `thread/name/set`, `thread/archive`, `thread/fork`, `thread/backgroundTerminals/list`, `turn/start`, `turn/steer`, and `turn/interrupt`. `thread/start` supports `ephemeral`; read-only ephemeral mode is used by live verification to avoid persistent thread/config effects. A just-created thread is provisional until its first user turn: if App Server rejects `thread/read(includeTurns: true)` as not materialized, the companion retries metadata-only read; if `thread/resume` reports that no rollout exists, it confirms the loaded thread by metadata-only read and treats resume as a no-op so `turn/start` can materialize it. Other RPC failures are not hidden.

The contextual Terminal is a monitor, not an execution surface. It forwards only the public, thread-scoped background-terminal list. An unloaded thread is resumed once before retry; an unmaterialized provisional thread or one owned by another local App Server writer returns a bounded unavailable reason. Although the generated schema also contains `thread/shellCommand`, `command/exec`, `process/spawn`, terminal mutation, and process-control methods, the companion exposes none of them.

Notifications stream over one companion-owned subscription and are scoped to browser thread sockets by `threadId`. The UI treats `turn/started` and `turn/completed` as authoritative for the primary run state, uses `item/agentMessage/delta` only to advance waiting to visible incremental text, and keeps item progress separate. Public `item/reasoning/summaryTextDelta` content is accumulated by item, with `summaryPartAdded.summaryIndex` represented as readable section boundaries. Hydrated reasoning uses only the public `summary`; raw reasoning `content` is not a fallback. Empty completed summaries are suppressed. `turn/completed.status` handles completed, failed, and interrupted outcomes. On socket reconnect the client rereads authoritative history, buffers notifications during hydration, and then applies them in order; it does not claim server-side event replay.

Current interactive approval UI supports `item/commandExecution/requestApproval` and `item/fileChange/requestApproval`. Responses use the generated v2 decision values `accept` and `decline`; unsupported server requests remain visible and can be rejected without inventing a response shape. A request leaves pending UI state only after the companion successfully writes the JSON-RPC response.

The realtime adapter implements the public experimental WebRTC transport: the browser can create an audio track and `oai-events` data channel, send its generated SDP through `thread/realtime/start` with `outputModality: "audio"`, `transport.type: "webrtc"`, and version `v3`, then apply `thread/realtime/sdp`. `thread/realtime/stop`, transcript, started, closed, and error notifications share the thread event socket. WebRTC version `v2` is rejected at the local HTTP model because upstream documents it as unsupported.

Availability is capability-gated rather than inferred from the experimental initialization capability alone. The Mac launcher applies Codex's documented process-scoped `--enable realtime_conversation` override without writing `config.toml`; managed requirements and other higher-precedence controls remain authoritative. The companion then queries `experimentalFeature/list`, verifies that a signed-in account exists when the selected provider requires OpenAI authentication, and requires a non-empty `thread/realtime/listVoices` result before enabling the microphone.

The WebRTC v3 path uses App Server's current authentication provider. Both the installed source and live probe support the reused ChatGPT account, so the companion has no API-key-only preflight and never reads `OPENAI_API_KEY`. It returns only capability state and user-safe reasons to the browser; bearer tokens, account identifiers, and attestation material stay outside browser JavaScript. Known App Server rejections become bounded 409/503 responses and actionable UI text; raw RPC payloads are not shown.

## Verification

- `backend/tests/test_codex_client.py` covers initialization capability negotiation, correlation, request lifecycle, current time, failure, and protocol bounds.
- `backend/tests/test_api.py` covers provisional-thread read/resume fallback, exact ephemeral thread/realtime/background-terminal request forwarding, active-writer limitation, ChatGPT-auth capability gating, bounded rejection mapping, and origin isolation.
- `frontend/src/api.test.ts` and `frontend/src/turn-lifecycle.test.ts` cover 0.147 item/delta/turn normalization, readable reasoning-summary sections, raw-reasoning exclusion, history hydration, optimistic reconciliation, terminal cleanup, and lifecycle races.
- `frontend/src/realtime.test.ts` verifies the microphone offer flow, `oai-events` data channel, v3 start, SDP answer, stop, cleanup, and friendly rejection states with browser fakes.
- `tools/smoke_app_server.py` performs the signed-in ephemeral thread and denied approval check while comparing `config.toml` digests.

## Gaps

- Add negotiated compatibility ranges instead of a documented tested version.
- Add real microphone/audio WebRTC evidence; current verification stops after enabled feature/account/voice discovery and deliberately does not request microphone permission or start a realtime session.
- Implement structured UI responses for request-user-input, permissions, and MCP elicitations before marking them supported.
