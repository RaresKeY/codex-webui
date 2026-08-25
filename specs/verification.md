# Verification

## Status

Automated backend/frontend checks implemented; live App Server smoke implemented and opt-in; browser visual evidence complete, audio evidence pending.

## Source Sync

- Check entrypoint: `tools/validate.sh`.
- Backend: `backend/tests/`.
- Frontend: `frontend/src/api.test.ts`, `frontend/src/token-format.test.ts`, `frontend/src/turn-lifecycle.test.ts`, `frontend/src/realtime.test.ts`, `frontend/src/context-tools.test.ts`, `frontend/src/event-groups.test.ts`, and `frontend/src/layout-contract.test.ts`.
- Live protocol: `tools/smoke_app_server.py` and `tools/probe_realtime_capability.py`.
- CI/container evidence: `.github/workflows/ci.yml`.

## Behavior

`tools/validate.sh` selects Python 3, runs backend pytest, then uses npm or pnpm for a clean/install-compatible frontend build, lint, and Vitest run. The Mac system Python 3.9 path is supported through the declared annotation-evaluation backport.

Backend coverage includes projects/workspace migration, settings/thread metadata and exact `thread/name/set` forwarding, scheduler lifecycle, update gating, authoritative thread parameters, provisional and ephemeral creation, approval lifecycle, current-time handling, protocol bounds, exact realtime/background-terminal forwarding, active-writer limitation, capability/rejection mapping, bounded Git changes, security policies, event scoping, configuration enums, and workspace traversal/symlinks. Frontend coverage includes authoritative history/turn/name status, deterministic local provisional-title derivation, waiting/delta/terminal transitions, optimistic message reconciliation, reconnect hydration state, readable reasoning-summary normalization and empty-summary suppression, consecutive command grouping with non-command boundaries, safe CommonMark/GFM structures, raw-HTML and unsafe-link rejection, partial-stream parsing and code-block copy presentation, item/context/usage normalization, K/M/B token formatting with exact accessible labels, realtime notifications and failure text, the browser WebRTC setup/cleanup contract, and the stable context-tool registry with backing-driven Outputs, read-only Terminal, Side chats, Explorer, Changes, and an honestly planned Browser.

The production frontend is also opened against the live Mac companion for visual inspection at the normal desktop viewport and at 760px width. Desktop geometry must resolve in left-to-right order as application rail, conversation navigation, flexible conversation, then context panel. The check switches Outputs, Terminal, Side chats, Browser, Explorer, and Changes; confirms backing-driven populated/empty/limited states; closes the context panel to confirm the conversation expands; and confirms the panel remains visually separate from the transcript. Command disclosure checks verify that the count group and every nested command are closed initially, outer expansion reveals command summaries without raw output, and a second expansion reveals only the selected command output. Conversation-navigation checks close and reopen the sidebar through the dedicated rail action, the active Chats action, and the header affordance that appears while closed. A live first-turn check must observe waiting before output, assistant text length increasing across samples, exactly one reconciled user message and assistant card, a list-level Working label, and no active indicators after terminal completion. It must also confirm a provisional chat hydrates without a history error and that capability discovery exposes an enabled mic without clicking it or requesting permission; unavailable/rejected paths remain covered by focused tests. The rename check opens the dialog from both title double-click and the pencil action, verifies the input is focused and the dialog remains centered over a muted full-page scrim, and exercises Escape dismissal at desktop and 760px width. The narrow-width check also verifies that entering the breakpoint closes both overlay drawers, that opening either drawer closes the other, and that the chat composer remains reachable.

The live smoke launches the installed host App Server with its existing login, creates an ephemeral read-only thread, starts a turn that requests a command approval, sends `decline`, waits for turn completion, verifies the marker was not created, and confirms the Codex config digest is unchanged. A separate read-only App Server probe launches with `--enable realtime_conversation`, confirms the effective feature plus non-empty voice discovery under ChatGPT auth, and stops without calling `thread/realtime/start` or requesting microphone permission. Neither check inspects or prints auth material.

## Verification

Evidence for this implementation pass is recorded in the final handoff and should include:

- backend pytest result and count;
- frontend production build, lint, and Vitest result/count;
- schema generator result/version;
- live thread/approval/config-digest smoke result;
- browser-controlled desktop and narrow-width observations, including named-grid geometry and context-tool state, or an explicit omission.

## Gaps

- Add durable automated browser tests and real microphone/speaker WebRTC evidence; capability discovery is verified, but media-session initiation was intentionally not performed in this pass.
- Add macOS CI, versioned migration/rollback tests, target-Pi hardware evidence, and performance budgets.
- Add a registry-manifest check if container publishing remains supported.
