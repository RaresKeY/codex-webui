VERDICT: APPROVE

SCOPE
- Current WebUI 2 chat, recent plugin/image/startup changes, sidebar metadata/icon, pending header-effort changes, and their workspace credential boundary.
- Normal checkout; existing pending work preserved. Production Firefox fixtures at 1440×1000 and 390×844, keyboard and touch input, and an isolated amd64 runtime.

FINDINGS
No actionable finding remains in this reviewed scope after patching and verification.

- `backend/app/workspace.py::resolve` previously allowed the configured Jev key file to be returned through the workspace browser. A synthetic configured key reproduced HTTP 200. Configured Jev and Codex-state paths, host mount aliases and canonical symlink aliases now reject read/write/image access; tree and change projections omit them. The launcher passes source paths without reading credential contents.
- `frontend/src/App.tsx::ChatSurface` previously unmounted on Projects/Tasks/Images/Settings navigation. Navigating while routing reproduced an aborted request, empty draft and permanently disabled composer showing “Thinking…”. The active chat now stays mounted while hidden, retaining text submissions and drafts; voice stops on hiding. Switching conversations retains cancellation.
- `frontend/src/App.tsx::ChatSidebar` accepted late replies from obsolete queries. Searches now cancel obsolete reads and bind results to the current trimmed query. A delayed alpha search cannot replace the later beta result.
- `frontend/src/MarkdownContent.tsx` resolved relative images against the workspace root. Relative Markdown previews now resolve against the conversation directory while absolute paths retain server containment. The production fixture decodes a project-relative preview and rejects the incorrectly rooted alternative.
- `frontend/src/Composer.tsx` retained hidden plugin selections after deleting their mentions. Deleting text now removes the selection immediately; manually restoring it does not silently activate the plugin. Unicode boundaries in `plugin-mentions.ts` agree with backend validation.

CHANGES
- Applied the five fixes above and added behavioral regression coverage.
- Preserved the quiet layout, sidebar details, new icon, pending model/effort display, single activity indicator, exact ask text, Jev → acknowledged model settings → submission ordering, and no automatic submission retries.
- Updated project specs and added optional browser bundle/output paths so checks can save isolated evidence.

VERIFICATION
- `.venv/bin/python -m pytest backend/tests -q`: 103 passed.
- `./tools/build-image.sh`: restricted offline Deno TypeScript/build/lint and 60 frontend tests; runtime-image backend tests, 103 passed; actual offline Codex plugin discovery, legacy history, model acknowledgements and synthetic routed submission passed.
- `python3 tools/check_browser.py --output-dir /tmp/webui2-review-evidence/acceptance`: desktop/phone checks passed with zero uncaught JavaScript errors. Includes navigation during a pending submission, edited draft retention, delayed search replies, deleted plugin selection, project-relative image decoding, prior routing/activity/context checks and explicit startup/history retry.
- Independent production Firefox metadata/icon checks: long titles/previews, project fallback, keyboard disclosure, touch disclosure, phone overflow and decoded versioned icon passed at both sizes.
- `navigation-before.png` and `navigation-after.png` document the reproduced failure and repaired navigation flow. Details and phone screenshots record the retained presentation.
- Isolated read-only, network-disabled runtime with disposable synthetic files: actual HTTP shell/icon/bootstrap responses passed; configured key/state reads, overwrites and symlink aliases returned 403. No real credentials were mounted and no inference was invoked.
- `sh -n tools/run-container.sh` and `git diff --check` passed.
- Retained image: `localhost/codex-webui-2:local`, `cba9c1df58ec231ab4d731d14d8d9c7fbfe1898aa48fef7e18e9c1fe1c22bf00`. The existing container was not restarted.

UNVERIFIED
- Paid Jev/Codex execution, real plugin execution, live microphone audio, ARM64 and a full accessibility audit.
- Credential exclusions protect configured canonical paths; they do not classify secrets in arbitrary project files or reduce native Codex authority. The documented ancestor-symlink race remains outside this change.
