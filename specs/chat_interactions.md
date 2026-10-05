# Chat interactions and startup

## Ownership

`frontend/src/Composer.tsx`, `plugin-mentions.ts`, `InlineImages.tsx`, `images.ts` and `context-usage.ts` project the installed App Server contract. `backend/app/plugins.py` validates plugin selections; `chat_service.py` retains execution ordering. `main.py` owns local shell data and bounded workspace image previews.

## Startup

`GET /api/bootstrap` returns local health/system/project/settings/task data without native RPCs, workspace scans or image enumeration. The interface opens before `/api/threads?limit=25`, `/api/models` and `/api/usage` finish. History has its own loading/error/explicit Retry state; arriving history preserves newly created/selected chats. Optional metadata failures preserve available values and the default two-model pool. Images and workspace files load when their surfaces open. Active conversation hydration blocks sending until its snapshot settles; switching conversation aborts obsolete browser reads, and newer hydration supersedes older results. Backend event forwarding also watches client disconnects, releasing idle subscriptions immediately.

Native RPCs have a configurable 30-second default deadline (`CODEX_WEBUI_CODEX_REQUEST_TIMEOUT_SECONDS`, greater than zero and at most 120). Timeout/cancellation removes pending futures and late responses are ignored. Browser GET deadlines cover response bodies: bootstrap 8 seconds, other reads 35 seconds. Failures do not substitute demo data. Retry requires a user action; text submission and model binding never automatically retry. A mutation timeout cannot prove that native execution did not start, so its message directs the user to check current state first.

## Plugin mentions

Typing `@` after a word boundary opens installed-plugin suggestions. Arrow keys navigate, Enter/Tab selects, Escape dismisses, and Shift+Enter remains a newline. Selecting inserts the plugin's literal `@name` and retains its catalog ID separately. Removing the mention removes it from the submitted selection. At most eight selected plugins are accepted. Text is preserved exactly, including whitespace.

`GET /api/plugins?cwd=...` calls native `plugin/installed` for a directory inside the configured workspace. Only installed, enabled, available entries are projected as ID/name/display name/description. Catalog failures have explicit error/retry feedback. The backend resolves IDs against a fresh catalog and requires the corresponding literal mention before spending on Jev. It appends native `UserInput` mention entries with `plugin://name@marketplace` paths after the unchanged text; callers cannot supply arbitrary native paths. Routing still receives the exact ask, then acknowledged model selection precedes `turn/start`. Discovery does not install or modify plugins.

## Presentation

One unboxed transcript indicator covers choosing, switching, sending, waiting and streaming. Empty assistant/reasoning events add no second placeholder or spinner. The composer keeps a disabled arrow while a send is active; the bottom activity plate and blinking text cursor are removed. Public thought summaries remain collapsible; raw reasoning deltas remain excluded.

Inline previews cover native user images/local images, image-view/image-generation items, raster tool content and Markdown image paths. Clicking opens a native dialog; Escape/Close restores focus to the preview. Raster data and app library URLs are accepted; local paths go through the workspace-rooted preview route. That route reads at most the configured 20 MiB image limit off the event loop, validates PNG/JPEG/GIF/WebP signatures and rejects traversal/symlink escape. HTTP remote images and SVG data are not fetched. Library loading/import/delete failures are visible.

The context ring uses latest `tokenUsage.last.totalTokens` against the reported `modelContextWindow`, rather than lifetime cumulative usage. Hover and keyboard focus disclose exact used/total/remaining token counts. Missing data stays unknown; a model selection clears stale context values until a fresh report arrives.

## Verification

`backend/tests/test_plugins.py`, `test_startup_and_previews.py`, `test_codex_client.py` and existing routed-chat tests cover safe discovery, enforced mentions, unchanged asks, no spending after invalid selections, deadlines and bounded previews. `frontend/src/chat-features.test.ts` and Markdown/API tests cover normalization, mention boundaries, read cancellation/deadlines and context totals. `tools/check_browser.py` runs production Firefox fixtures at 1440×1000 and 390×844 with no paid calls. Its optional `--baseline-bundle` captures equivalent states from the prior runtime bundle. `tools/check_thread_lifecycle.py` exercises native plugin discovery with disposable state and network disabled.

## Gaps

- Plugin APIs are experimental in the installed 0.160.0 schema; execution with a real installed plugin and paid model transports remains unverified.
- Image file IDs alone, remote images, image attachment sending, full decode/dimension limits and importing generated previews into the library remain outside this subset.
- Native thread history does not restore token-usage totals; reopened chats show unknown context until a notification arrives.
- Browser evidence uses Firefox fixtures and does not claim a full accessibility audit or live microphone coverage.
