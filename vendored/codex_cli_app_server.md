# Codex CLI and App Server

Codex is the external runtime for authentication, threads, execution, approvals, sandbox policy, events, usage, and realtime. This repository owns only its localhost adapter and browser projection.

## Compatibility record

- Inherited adapter: official standalone 0.147.0 at original implementation time. WebUI 2 generates the 0.160.0 schema and packages that workstation standalone release; paid live smoke is unverified here.
- Schema source: `codex app-server generate-ts --experimental` and `generate-json-schema --experimental` from that executable.
- Release source reference: `openai/codex` tag `rust-v0.147.0` (`be6e8eac029b183056b7e4402879f15d2c85f61b`).
- Additional local open-source reference: `openai/codex` commit `4861236f06d0df397436531b4aa3d7fa6975959c` (2026-08-15).
- Transport: one companion-owned stdio JSONL process; JSON-RPC 2.0 header omitted on the wire as documented.
- Internal owner: `backend/app/codex_client.py`.

Primary references:

- [Codex App Server README](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md)
- [Codex repository](https://github.com/openai/codex)
- [Official Codex CLI install/update documentation](https://developers.openai.com/codex/cli)
- [Official App Server contract](https://learn.chatgpt.com/docs/app-server)

## Used protocol subset

Initialization is `initialize` then `initialized`, with `capabilities.experimentalApi: true` and `requestAttestation: false`. The client uses current v2 thread/turn methods, account/model/usage reads, the read-only `thread/backgroundTerminals/list` inventory, `currentTime/read`, command and file approval requests, and exact `accept`/`decline` decisions.

The generated ClientRequest union has no browser-tab, navigation, DOM, or screenshot method. Codex Desktop's in-app Browser remains outside this standalone client's public integration boundary. This branch instead registers a companion-owned `browser` through the verified CLI 0.160.1 `thread/start.dynamicTools` extension (`type: function`, `name`, `description`, `inputSchema`) and handles `item/tool/call` with `success`/`contentItems` (`inputText`). The generated 0.160.1 resume schema has no dynamicTools field. This extension is version-gated and does not imply compatibility with 0.147.0. The same union does contain generic shell/command/process and background-terminal mutation methods; the companion deliberately projects none of those, exposing only Codex-driven output notifications and read-only terminal metadata. Public reasoning summaries arrive through `item/reasoning/summaryTextDelta` plus `summaryPartAdded` boundaries and through the hydrated reasoning item's `summary`; its separate raw `content` is not presentation-safe fallback material. `thread/name/set` returns an empty object and publishes the durable value separately through `thread/name/updated`, whose nullable `threadName` clears a name.

Realtime is experimental but public in the generated schema. The browser follows the upstream WebRTC example: audio track plus `oai-events` data channel before `createOffer()`, `thread/realtime/start` with the browser SDP, `thread/realtime/sdp` for the answer, and `thread/realtime/stop` for teardown. The client requests version `v3`; the upstream implementation accepts WebRTC v1/v3 and rejects v2. The stable CLI lists `realtime_conversation` as under development and off by default. The local launcher uses its supported process-scoped `--enable realtime_conversation` flag, then verifies effective feature state, required account presence, and voices. Inherited source and no-session probe evidence indicated that WebRTC v3 uses the existing ChatGPT auth provider; only the legacy direct WebSocket path has the API-key-only helper.

0.160.0 schema verification includes `ThreadStartParams.historyMode`. The current runtime selected paginated history when this field was omitted but rejected full reads and resume with `list_turns is not supported yet`. The WebUI explicitly requests legacy history for new threads; incompatible existing threads receive a recovery instruction without history mutation. `tools/check_thread_lifecycle.py` now verifies the actual packaged backend/binary offline with fresh temporary state.

The installed schema also defines `thread/loaded/list` and `thread/settings/update` with model/effort inputs and an empty-object acknowledgement. The general App Server documentation confirms the turn model/effort fields but does not document this settings method; its contract comes from the installed generated schema and native offline checks. Fresh loaded threads accept settings updates for both routing models before their first turn. Chat submission awaits that response, then sends matching model/effort through `turn/start`; a failed provisional resume or a metadata read cannot stand in for acknowledgement. Direct HTTP `turn/steer` execution is no longer exposed.

Required 0.147 sandbox-policy fields are preserved: read-only includes `networkAccess`; workspace-write includes `writableRoots`, `networkAccess`, `excludeTmpdirEnvVar`, and `excludeSlashTmp`.

Additional installed 0.160.0 schema inspection covers `SkillsListParams.cwds`, enabled `SkillMetadata` and native `{type: "skill", name, path}` inputs; `AppsInstalledParams` accepts only a loaded optional thread ID, with enabled/callable runtime entries; `app/read` supplies display metadata and selected apps use `app://id` mention paths. Discovery does not set refresh flags or request tools. `fuzzyFileSearch` returns rooted matches used for canonical workspace references. The combined menu exposes these supported categories without claiming every CLI command or elicitation flow. Native offline checks discover a disposable project skill and file; connected-app execution remains unverified.

The installed 0.160.0 schema defines `plugin/installed` with `cwds`, marketplace entries containing installed/enabled/availability flags, and native `UserInput` mention entries. The packaged executable's plugin parser confirms canonical `plugin://name@marketplace` paths. General App Server documentation labels plugin APIs experimental; the adapter only reads installed metadata. `ImageGenerationItem.result/savedPath/failure`, image-view paths, user/tool image content and `ThreadTokenUsage.last/modelContextWindow` are inspected schema fields used by the frontend. Offline native discovery and fixture mention/image/context tests cover this subset without plugin execution or inference.

The companion uses existing Codex environment/login resolution with externally mounted state in the container and never reads private auth layouts. It does not communicate with or patch the desktop app. The runtime feature argument does not persist configuration. `tools/smoke_app_server.py` uses an ephemeral read-only thread and a denied approval, then compares config digests.

The installed 0.160.0 schema also defines `ThreadSettingsUpdateParams` permission fields (`approvalPolicy`, `approvalsReviewer`, `sandboxPolicy`), the same sticky overrides on `TurnStartParams`, and `ThreadSettingsUpdatedNotification.threadSettings` with effective policies. Public `ApprovalsReviewer` includes `user`, `auto_review` and the legacy `guardian_subagent`; the UI selects only the first two. Full-access presets use legacy-compatible `{type: "dangerFullAccess"}`; workspace defaults retain required explicit policy fields. Settings update acknowledges with `{}`. Provisional threads may have no native rollout yet, so permission persistence uses the companion's bounded per-chat setting and reapplication before text execution rather than a resumable-history assumption. Official reviewer semantics are described in [automatic approval reviews](https://learn.chatgpt.com/docs/agent-approvals-security#automatic-approval-reviews); installed schema and offline native notifications supply the exact settings-method contract.

Response branching is pinned to the installed `codex-cli 0.160.1` JSON schema: `ThreadForkParams.lastTurnId` is inclusive and cannot target an in-progress turn; `deferGoalContinuation: true` prevents automatic goal continuation after a fork. The app exposes a strict turn ID rather than arbitrary fork config/path overrides. Native `Turn.startedAt`/`completedAt` use Unix seconds, `durationMs` milliseconds; `agentMessage.phase` can be commentary/final_answer/null. Web-search results are opaque JSON, so only bounded URL/title fields are projected. See `specs/turn_presentation.md` and adapter tests; no upstream update was performed.

## Gaps

- WebUI 2 packages standalone 0.160.0 rather than the original npm-installed runtime; live text/voice integration requires separate evidence.
- There is no declared semantic compatibility range or automatic method negotiation beyond initialization opt-in.
- Re-run schema generation and adapter/live tests for every supported Codex CLI upgrade.

Chat lifecycle uses `thread/archive`, `thread/unarchive`, and `thread/delete` with `{threadId}`. Installed v0.160.0 schemas and offline disposable-home checks confirm empty archive/delete acknowledgements and a returned thread for restore. Native deletion includes spawned descendants; no direct native-file unlinking is used.
