# Codex App Server contract

## Status

Inherited adapter subset originally authored for 0.147.0; 0.160.0 schema verified for thread loading/settings and turn model/effort fields. WebUI 2 enforces Jev-first text chat in the backend; see jev_routing.md. Live paid execution is unverified in this project.

## Source Sync

- `backend/app/codex_client.py`: stdio ownership, initialization, correlation, server requests, subscriptions, and shutdown.
- `backend/app/main.py`: HTTP/WebSocket projection for threads, turns, approvals, and realtime.
- `backend/app/chat_service.py`: server-owned routing, loading, acknowledged settings update and exact-input turn submission.
- `backend/app/models.py` and `backend/app/config.py`: accepted client inputs and wire-policy conversion.
- `frontend/src/api.ts`, `frontend/src/realtime.ts`, and `frontend/src/app-server-protocol.ts`: event normalization, exact protocol subset, and browser WebRTC leg.
- `tools/generate-app-server-schema.sh` and `tools/smoke_app_server.py`: schema drift and opt-in live verification.

Any change to these protocol calls or payloads requires this spec, adapter tests, and the vendored compatibility note to change in the same turn.

## Behavior

Codex owns authentication, threads, turns, execution, approvals, sandbox policy, usage, and realtime sessions. The app owns presentation and local organization. A conversation stores and uses the upstream thread ID; transcript text never substitutes for native continuation.

The companion directly launches its configured `codex app-server` with inherited environment and stdio JSONL. The container points `CODEX_HOME` at externally mounted state (`/codex`); it does not copy login files into the image, parse private auth state, or communicate with the Codex desktop app. Initialization sends one `initialize` request followed by `initialized` and declares:

```json
{"experimentalApi": true, "requestAttestation": false}
```

The experimental opt-in is required by the public realtime methods. This client does not claim desktop attestation support. The adapter correlates numeric client request IDs, retains server-initiated requests, automatically answers `currentTime/read`, drains stderr without retaining it, caps protocol lines at 32 MiB, and clears requests on server resolution or disconnect.

WebUI-created durable threads explicitly request `historyMode: "legacy"`, including new scheduler threads. In the installed 0.160.0 runtime with current external state, omitting this field created paginated threads that refused full reads and resume with `list_turns is not supported yet`. The adapter uses the supported legacy path for new threads and returns a bounded 409 with a New chat recovery instruction for existing incompatible threads. It does not rewrite stored history, substitute an empty transcript, or replay asks.

The supported thread/turn surface is `thread/list`, `thread/read`, `thread/start`, `thread/loaded/list`, `thread/resume`, `thread/settings/update`, `thread/name/set`, `thread/archive`, `thread/fork`, `thread/backgroundTerminals/list`, `turn/start`, and `turn/interrupt`. Direct steering is rejected at the HTTP boundary. `thread/start` supports `ephemeral` but accepts no prompt; read-only ephemeral mode is used by live verification to avoid persistent thread/config effects. A just-created thread is provisional until its first user turn: if App Server rejects `thread/read(includeTurns: true)` as not materialized, the companion retries metadata-only read for history hydration only. That read does not acknowledge a model change.

The installed 0.160.0 schema defines `ThreadLoadedListResponse.data` as thread IDs and `ThreadSettingsUpdateParams` with `threadId`, `model` and `effort`; `ThreadSettingsUpdateResponse` is an empty object. The companion first checks loaded IDs, resumes an unloaded thread once with `excludeTurns: true`, then applies settings and requires the actual correlated empty-object acknowledgement. Loaded provisional threads accept this settings update before their first turn. Failed resume/settings calls stop submission; there is no metadata-only fallback for either. The public `/resume` endpoint uses this same loading/binding path and reports `modelChangeAcknowledged` only after a requested model update succeeds. Chat sends always bind the Jev-selected model/effort themselves before `turn/start`.

The contextual Terminal is a monitor, not an execution surface. It forwards only the public, thread-scoped background-terminal list. An unloaded thread is resumed once before retry; an unmaterialized provisional thread or one owned by another local App Server writer returns a bounded unavailable reason. Although the generated schema also contains `thread/shellCommand`, `command/exec`, `process/spawn`, terminal mutation, and process-control methods, the companion exposes none of them.

Notifications stream over one companion-owned subscription and are scoped to browser thread sockets by `threadId`. After acknowledging the settings update, the companion publishes `webui/modelSelected` on that same ordered channel before dispatching the turn; the browser updates model provenance before processing subsequent native items. The UI treats `turn/started` and `turn/completed` as authoritative for the primary run state, uses `item/agentMessage/delta` only to advance waiting to visible incremental text, and keeps item progress separate. Public `item/reasoning/summaryTextDelta` content is accumulated by item, with `summaryPartAdded.summaryIndex` represented as readable section boundaries. Hydrated reasoning uses only the public `summary`; raw reasoning `content` is not a fallback. Empty completed summaries are suppressed. Conversation naming updates visible state optimistically around `thread/name/set`, then reconciles the canonical value from `thread/name/updated`; the RPC result itself contains no name. `turn/completed.status` handles completed, failed, and interrupted outcomes. On socket reconnect the client rereads authoritative history, buffers notifications during hydration, and then applies them in order; it does not claim server-side event replay.

Current interactive approval UI supports `item/commandExecution/requestApproval` and `item/fileChange/requestApproval`. Responses use the generated v2 decision values `accept` and `decline`; unsupported server requests remain visible and can be rejected without inventing a response shape. A request leaves pending UI state only after the companion successfully writes the JSON-RPC response.

The realtime adapter implements the public experimental WebRTC transport: the browser can create an audio track and `oai-events` data channel, send its generated SDP through `thread/realtime/start` with `outputModality: "audio"`, `transport.type: "webrtc"`, and version `v3`, then apply `thread/realtime/sdp`. `thread/realtime/stop`, transcript, started, closed, and error notifications share the thread event socket. WebRTC version `v2` is rejected at the local HTTP model because upstream documents it as unsupported.

Availability is capability-gated rather than inferred from the experimental initialization capability alone. The local launcher applies Codex's documented process-scoped `--enable realtime_conversation` override without writing `config.toml`; managed requirements and other higher-precedence controls remain authoritative. The localhost-companion mode then queries `experimentalFeature/list`, verifies that a signed-in account exists when the selected provider requires OpenAI authentication, and requires a non-empty `thread/realtime/listVoices` result before enabling the microphone.

The WebRTC v3 path uses App Server's current authentication provider. Inherited source/probe evidence supported the reused ChatGPT account, so the companion has no API-key-only preflight and never reads `OPENAI_API_KEY`. It returns only capability state and user-safe reasons to the browser; bearer tokens, account identifiers, and attestation material stay outside browser JavaScript. Known App Server rejections become bounded 409/503 responses and actionable UI text; raw RPC payloads are not shown.

## Verification

- `backend/tests/test_codex_client.py` covers initialization capability negotiation, correlation, request lifecycle, current time, failure, and protocol bounds.
- `backend/tests/test_api.py` covers provisional-thread history hydration, actual model-change acknowledgement, exact ephemeral thread/realtime/background-terminal request forwarding, active-writer limitation, ChatGPT-auth capability gating, bounded rejection mapping, and origin isolation.
- `backend/tests/test_routed_chat.py` covers direct-call enforcement, exact text/model/effort, loaded/resume/settings ordering, delayed and failed acknowledgements, rejection of metadata as acknowledgement, streamed results and cancellation/concurrency.
- `frontend/src/api.test.ts`, `frontend/src/conversation-title.test.ts`, and `frontend/src/turn-lifecycle.test.ts` cover 0.147 item/delta/turn/name normalization, deterministic provisional naming, readable reasoning-summary sections, raw-reasoning exclusion, history hydration, optimistic reconciliation, terminal cleanup, and lifecycle races.
- `frontend/src/realtime.test.ts` verifies the microphone offer flow, `oai-events` data channel, v3 start, SDP answer, stop, cleanup, and friendly rejection states with browser fakes.
- `tools/check_thread_lifecycle.py` checks the packaged backend and actual installed binary in an offline container with disposable Codex state: legacy creation, new-thread history hydration, and real acknowledged settings updates for both models. It also checks a complete routed send with native loading/settings calls and only Jev/inference transport replaced by fixtures. No actual inference request is sent.
- `tools/smoke_app_server.py` performs the signed-in ephemeral thread and denied approval check while comparing `config.toml` digests.

## Gaps

- Add negotiated compatibility ranges instead of a documented tested version.
- Container voice capability remains disabled by the inherited runtime gate; no live voice support is claimed.
- Add real microphone/audio WebRTC evidence; current verification stops after enabled feature/account/voice discovery and deliberately does not request microphone permission or start a realtime session.
- Implement structured UI responses for request-user-input, permissions, and MCP elicitations before marking them supported.
