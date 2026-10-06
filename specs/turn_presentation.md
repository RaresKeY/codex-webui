# Turn presentation and response branches

The chat header has a Sources and outputs toggle. It pins a compact card below the header at the right edge of the current chat, independently of the full context pane. Opening the full context pane hides the compact card; closing it restores the current chat's toggle state. Escape and Close restore toggle focus. The card overlays the chat without changing transcript, Worked row or composer alignment at any width. Entering the narrow layout (viewport at most 1000px) automatically closes the summary; the header toggle can reopen its bounded, scrollable overlay on a phone. No polling or external image/favicon requests are introduced.

Sources are deduplicated HTTP(S) URLs from native web-search result/action items and assistant Markdown links, with a website icon, title and hostname. Credential-bearing URLs and other protocols are rejected. Markdown images, user links, inline/fenced/indented code examples and unsupported opaque result shapes are excluded. Outputs list native file-change paths and generated images; failed file changes are excluded. View outputs opens the existing conversation Outputs pane, which also displays inline image previews. Lists are bounded to 100 entries; the compact card initially shows four sources and four outputs. Empty states disclose missing resources without invented links or file/site creation controls.

Turn work, command groups, file changes and reasoning use the shared activity presentation described in [work_activity.md](work_activity.md).

Completed assistant responses have Copy and Branch chat from here actions, without ratings. Desktop action buttons use compact 28px widths with a 2px gap and a small timestamp inset; coarse-pointer devices retain larger touch targets. Hover/focus feedback uses the existing neutral theme. Native `completedAt` supplies a locale-formatted time beside the actions, visible on message hover or keyboard focus and directly on devices without hover. Missing native timestamps stay absent. Branch is available at the last visible reply of a native turn with a terminal status, because the native boundary includes that whole turn; unknown IDs/timing are not synthesized from display labels.

`POST /api/threads/{id}/fork` accepts an optional strict `{turn_id}` body. With a body, the verified Codex 0.160.1 adapter reads native history, checks the requested terminal turn and rooted workspace, then calls native `thread/fork` with inclusive `lastTurnId` and `deferGoalContinuation: true`. Later turns are omitted, the source is unchanged, and no prompt, routing or inference is requested. The new native ID must be acknowledged before the UI opens its history. Duplicate action clicks are guarded; errors remain on the source response. The legacy no-body endpoint still forks the full chat, also deferring goal continuation.

After native acknowledgement, one optional SQLite transaction retains project assignment, per-chat permission/execution choices and model/effort selections for returned retained turn IDs. New branches are unpinned. Jev activity records are not copied: branching did not invoke Jev. Optional metadata failure returns `metadataSaved: false` with the successful native branch rather than causing a retry. No schema change or migration is needed; rollback removes presentation/routes while existing preferences remain readable.

Source ownership: `frontend/src/chat-resources.ts`, `ChatSummary.tsx`, `WorkActivity.tsx`, `App.tsx`, `api.ts`, `types.ts`, `styles.css`; `backend/app/main.py`, `models.py`.

Verification: `backend/tests/test_response_fork.py`, `frontend/src/chat-resources.test.ts`, API lifecycle tests, `tools/check_turn_browser.py` using synthetic native history at 1440×1000, 390×844 and 320×640. The browser fixture checks the actual rendered collapse/expand state, pinned summary, deduplication, hover/focus time, exact older-turn branching, visible errors, duplicate-click prevention and absence of ratings/inference.

Each Markdown table has its own Soft wrap table toggle. Default presentation preserves horizontal scrolling and unwrapped cells; wrapping uses the available table width with breakable cell/code content. Toggle state is local to the rendered table.

## Gaps

- Paid end-to-end branching of a real completed model turn remains opt-in and unverified; adapter fixtures and the installed native schema verify the inclusive/deferred contract.
- Older native turns can lack phase, duration, timestamps or recorded model/effort. Unknown commentary remains visible for compatibility.
- Only documented bounded URL/title result fields are projected; unsupported result shapes, non-Markdown citations and non-file/image artifacts can be absent.
- Optional organization copying may fail as a whole; native branch history remains authoritative.
- The compact toggle is current-chat component state, not a persisted cross-session preference. No accessibility audit or ARM64 runtime proof is claimed.
