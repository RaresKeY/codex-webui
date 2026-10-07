# Chat interactions and startup

## Ownership

`frontend/src/Composer.tsx`, `mentions.ts`, `InlineImages.tsx`, `images.ts` and `context-usage.ts` project the installed App Server contract. `backend/app/mentions.py` and `plugins.py` validate explicit selections; `chat_service.py` retains execution ordering. `main.py` owns local shell data and bounded workspace image previews.

## Startup

`GET /api/bootstrap` returns local health/system/project/settings/task data without native RPCs, workspace scans or image enumeration. The interface opens before `/api/threads?limit=25`, `/api/models` and `/api/usage` finish. History has its own loading/error/explicit Retry state; arriving history preserves newly created/selected chats. Optional metadata failures preserve available values and the default two-model pool. Images and workspace files load when their surfaces open. Active conversation hydration blocks sending until its snapshot settles; switching conversation aborts obsolete browser reads, and newer hydration supersedes older results. Backend event forwarding also watches client disconnects, releasing idle subscriptions immediately. Opening Projects, Tasks, Images or Settings hides the active chat while retaining its draft and pending text submission; switching conversations still cancels obsolete submission. Voice stops when the chat is hidden. Sidebar search cancels obsolete reads, scopes results to the current trimmed query and ignores late replies.

Native RPCs have a configurable 30-second default deadline (`CODEX_WEBUI_CODEX_REQUEST_TIMEOUT_SECONDS`, greater than zero and at most 120). Timeout/cancellation removes pending futures and late responses are ignored. Both global and per-chat event sockets watch disconnects while forwarding notifications, release idle subscriptions and cancel their companion tasks on exit. Browser GET deadlines cover response bodies: bootstrap 8 seconds, other reads 35 seconds. Failures do not substitute demo data. Retry requires a user action; text submission and model binding never automatically retry. A mutation timeout cannot prove that native execution did not start, so its message directs the user to check current state first.

## Skills, plugins, apps and files

Typing `@` or `$` after a word boundary opens enabled skills, available installed plugins, callable apps and matching workspace files. Twelve suggestions are interleaved across categories; typing narrows the menu. Arrow keys navigate and scroll the active option into view, Enter/Tab selects, Escape dismisses, and Shift+Enter remains a newline. Selection inserts native `$skill`, `$app`, `@plugin` or `@relative/file` syntax and retains its catalog ID separately. The caret is restored during the insertion's layout commit, so a delayed animation frame cannot move it behind subsequent typing. Plugin-owned skills include their namespace; file paths with spaces are quoted. Removing an invocation drops its hidden selection immediately; retyping it does not restore structured selection. Unicode boundaries match backend validation. At most eight selections across all categories and the legacy plugin field are accepted. Text is preserved exactly, including whitespace.

`GET /api/mentions?cwd=...&thread_id=...` uses native `skills/list`, `plugin/installed`, `app/installed` and `app/read`. Bounded names/descriptions/invocations are public; opaque skill IDs hide native absolute skill paths. Failed categories have explicit error/Retry feedback without hiding successful categories; valid skills survive unrelated skill-load errors. Apps use effective configuration for loaded threads and the global snapshot for unopened history. Selected apps load the conversation before revalidating callable state. Discovery does not install, write configuration or refresh the runtime. `/api/plugins` and the old `plugins` submission field remain compatible.

`GET /api/mention-files?cwd=...&q=...` uses native `fuzzyFileSearch` after a 200 ms browser debounce. Results and selected IDs are canonicalized inside the chat/workspace root, reject protected credentials/state and symlink escapes, and never read file contents. Obsolete searches are aborted and results are scoped to the query. File references remain in the exact ask; no undocumented file input type is synthesized.

Before spending on Jev, selected IDs resolve against fresh catalogs and require their literal invocation. The backend appends native `UserInput` skill entries or mentions with `plugin://name@marketplace` and `app://id` paths after unchanged text; callers cannot supply arbitrary native paths. Routing still receives the exact ask, then acknowledged model/effort selection precedes `turn/start`.

## Presentation

Markdown code blocks and table cells soft-wrap by default, including long unbroken tokens. Code indentation and explicit line breaks remain preserved; copying retains the original code text.

Jev process details appear only in the contextual sidebar tab, with event-driven stage updates and no timed history refresh. Responses contain no Jev process control. See `jev_activity.md`.

Markdown table and code headers use the sidebar's neutral dark surface. Shared surface, border, text, interaction and semantic colors are centralized in `frontend/src/theme.css`; see `color_theme.md`. Wide tables retain contained horizontal scrolling.

The composer Permissions button selects Default, Full access with automatic approval review, or Full access YOLO for this chat. Native acknowledgement precedes the visible label change, and saving blocks new submissions. The server reapplies saved permissions with the Jev-selected model before each ask; see `chat_permissions.md`.

One unboxed transcript indicator covers choosing, switching, sending, waiting and streaming. Empty assistant/reasoning events add no second placeholder or spinner. The composer keeps a disabled arrow while a send is active; the bottom activity plate and blinking text cursor are removed. Public thought summaries remain collapsible; raw reasoning deltas remain excluded.

Inline previews cover native user images/local images, image-view/image-generation items, raster tool content and Markdown image paths. Clicking opens a native dialog; Escape/Close restores focus to the preview. Raster data and app library URLs are accepted; local paths go through the workspace-rooted preview route. Relative Markdown image paths resolve against the conversation directory; absolute paths retain their configured workspace boundary. That route reads at most the configured 20 MiB image limit off the event loop, validates PNG/JPEG/GIF/WebP signatures and rejects traversal/symlink escape. HTTP remote images and SVG data are not fetched. Library loading/import/delete failures are visible.

The context ring uses latest `tokenUsage.last.totalTokens` against the reported `modelContextWindow`, rather than lifetime cumulative usage. Hover and keyboard focus disclose exact used/total/remaining token counts. Missing data stays unknown; a model selection clears stale context values until a fresh report arrives.

Each assistant message/image shows model and reasoning effort beside “Codex”. Ordered `webui/modelSelected` notifications carry both before native output. Successful WebUI turns save only thread ID, turn ID, model and effort in SQLite; reads enrich matching turns so labels survive reopening and later model changes. The Auto header restores the latest reply's recorded model and effort when reopening a chat; a new routing decision and an explicitly saved manual choice take precedence. A new chat or a latest reply without recorded effort keeps the Auto header at Jev until a choice arrives. Native history lacks effort, so old/unrecorded turns show “effort unknown”. A metadata write failure cannot turn an already acknowledged submission into a failed-send/retry condition.

## Verification

`backend/tests/test_mentions.py`, `test_plugins.py`, `test_database.py` and routed-chat tests cover discovery, partial failures, thread-effective apps, exact asks, rejected selections before spending and durable per-turn labels. Frontend mention/Markdown/API tests cover projection and boundaries. `tools/check_browser.py` runs production Firefox fixtures at 1440×1000 and 390×844 without paid calls, including all four selection types, dense keyboard scrolling and distinct historical/live efforts. `tools/check_thread_lifecycle.py` checks native skill/plugin/app discovery and rooted fuzzy files with disposable state and network disabled.

The composer also offers a shield for per-chat permissions and a speedometer for per-chat Auto/manual model and effort selection. Mobile controls use accessible icon buttons matching the supplied reference, with labels in their menus. Manual settings persist separately from per-turn provenance; the header reflects the saved choice before sending. New chats copy the latest explicitly acknowledged permission preset while existing chats retain theirs. See `chat_permissions.md` and `jev_routing.md`.

The context ring is in the composer immediately before the execution/model control. Hover, focus or tap opens a small tooltip above it with context-window percentage used/left and compact used/total tokens. Exact totals remain in the accessible label; unknown usage/limits stay explicit. Escape/blur closes it. A body portal and clamped viewport coordinates keep it visible on narrow screens; context remains based on the latest native context total. Header context duplication is removed.

See [turn_presentation.md](turn_presentation.md) for the pinned Sources/Outputs card, turn work disclosure, hover timestamps and inclusive native response branching with retained selection/preferences copying.

The composer and chat header use the same selected model/effort projection, including live routing-stage decisions and native acknowledgement. A previous reply’s model cannot mask a newer selection in the composer.

## Gaps

- Catalog/input APIs use the installed 0.160.0 schema; real skill/plugin/app execution and paid model transports remain unverified. Explicit selections are revalidated, but manually typed native `$` syntax can still be interpreted by Codex itself.
- This menu covers supported skill/plugin/app/file references, not every CLI slash command, configuration control, MCP elicitation or attachment flow.
- Old/native external turns lack recorded effort; automatic metadata retention is not implemented.
- Image file IDs alone, remote images, image attachment sending, full decode/dimension limits and importing generated previews into the library remain outside this subset.
- Native thread history does not restore token-usage totals; reopened chats show unknown context until a notification arrives.
- Browser evidence uses Firefox fixtures and does not claim a full accessibility audit or live microphone coverage.
