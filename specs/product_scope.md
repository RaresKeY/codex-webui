# Product scope

## Status

Partial local Mac client MVP.

## Source Sync

- Product UI: `frontend/src/App.tsx`, `frontend/src/context-tools.ts`, and `frontend/src/styles.css`.
- Browser behavior: `frontend/src/api.ts` and `frontend/src/realtime.ts`.
- Service surface: `backend/app/main.py`.
- Local launch: `tools/run-mac.sh`.

## Behavior

Codex Web UI is a single-operator browser client for the Codex CLI installed on the same Mac. It organizes native Codex threads into local projects while preserving upstream thread identity and host workspace paths.

The desktop shell is an explicit named grid: a stable application rail, project/conversation navigation, the flexible primary conversation, and an independently collapsible right context panel. The named areas keep the transcript centered and prevent an optional tool from taking the primary content column.

The UI provides authoritative thread search/list/read/create/resume/name, live agent/reasoning/command/file streams, command and file approvals, context usage, workspace browsing/editing, project organization, schedules, images, and settings. After the first turn is accepted, an otherwise untitled conversation receives a deterministic provisional name derived locally from the first meaningful prompt line; this path makes no model call, never replaces an existing name, updates visible state immediately, and persists through `thread/name/set`. The header also supports explicit manual rename. Sending a prompt immediately marks its conversation and open surface as active; the waiting card remains before the first assistant chunk, transcript deltas grow one assistant message, and authoritative completed/failed/interrupted events remove the turn-level indicators. Assistant messages and public reasoning/plan text render accumulated CommonMark plus GitHub-flavored tables, task lists, and strikethrough while streaming. Raw HTML is disabled, unsafe URL schemes are rejected, links open with isolation, and fenced code retains a copy action. User prompts, command output, file changes, approvals, and status events remain literal text. Readable reasoning-summary deltas retain their public section boundaries; raw reasoning content is not used as a display fallback, and completed reasoning items with no readable summary leave no empty card. Command/file cards keep their own item-level spinner. Auto-scroll follows only while the reader remains near the bottom.

The context panel uses a shared tool registry: Outputs, read-only thread background processes, related Side chats, Explorer, and bounded Git Changes are functional. Browser remains a visible planned surface because the installed public schema has no browser-control method; it does not call an invented or Desktop-private API. A public WebRTC voice adapter exists, but the microphone is enabled only after the companion verifies the per-thread CLI feature, compatible auth, and voices. The Mac launcher enables the installed CLI's supported process-scoped realtime feature; a read-only probe then verifies that the reused ChatGPT login and voice inventory satisfy those checks without starting a voice call or exposing credentials to the browser.

At widths of 1000px or less, the conversation-navigation and context drawers are mutually exclusive and close when a main view is selected. Entering the narrow layout closes both drawers so the active chat remains visible.

The companion reuses the existing Codex login and host toolchain. It does not alter, inject into, or automate the Codex desktop app. Bootstrap non-goals include public hosting, multi-user collaboration, replacing Codex authentication/policy, unrestricted terminal endpoints, two-way cloud conflict resolution, and silent self-update.

## Verification

Backend and frontend unit/integration tests cover the implemented service/UI adapters, lifecycle reducer, and context-tool registry. The opt-in live smoke covers native thread creation and a denied approval without a workspace or config change. Browser-controlled live checks verify named desktop order, context-tool switching, panel collapse, the production build at desktop and narrow layouts, capability-gated voice, provisional-chat hydration, waiting-before-output, growing response text, de-duplication, and terminal indicator cleanup.

## Gaps

- Add durable browser regression automation, broader accessibility evidence, and real microphone/speaker voice-call evidence; capability discovery alone does not prove end-to-end media succeeds for the account and network.
- Decide whether native Dock/menu-bar packaging is product scope or whether localhost + browser remains the client shell.
- Project/schedule/image lifecycle depth remains incomplete.
