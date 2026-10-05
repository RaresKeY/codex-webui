VERDICT: APPROVE

SCOPE
- Requested chat/startup changes and routed-send compatibility in the normal checkout; existing sidebar/details and header-effort work preserved.
- Production Firefox at 1440×1000 and 390×844, keyboard and pointer interactions, synthetic transcripts/events; current amd64 rootless runtime on loopback.

FINDINGS
No actionable finding remains in the requested changes after fixes and verification.

- Startup previously awaited native history/metadata with no read deadline. `backend/app/main.py:222`, `codex_client.py::request` and `frontend/src/App.tsx` now open the shell independently, bound reads and expose explicit retry. Idle WebSocket forwarding now consumes disconnects and releases subscriptions.
- `frontend/src/Composer.tsx` now projects installed plugins at @ and preserves exact drafts and edits during acknowledgement. `backend/app/plugins.py` revalidates native IDs and literal mentions before Jev; unavailable selections do not spend or execute.
- `frontend/src/InlineImages.tsx` and `api.ts::normalizeItem` display native history/live raster images and local Markdown previews, with zoom/Escape/focus restoration. Rooted server previews reject traversal, unsupported bytes and oversize files.
- `frontend/src/App.tsx:312` replaces the three message spinners with one unboxed indicator. The bottom plate, empty assistant placeholder, busy send-button spinner and text cursor animation are removed.
- `frontend/src/context-usage.ts` uses latest context occupancy and reported capacity, exposes exact used/total/remaining counts on hover/focus, and keeps unknown/stale values explicit.

CHANGES
- Added progressive startup, deadlines/cancellation, explicit bootstrap/history errors and independent image/file loading.
- Added @ plugin selection and validated native mention metadata while retaining Jev → actual settings acknowledgement → exact ask.
- Added history/live image previews and library error/zoom feedback; simplified turn activity and context totals.
- Fixed `/api/conversations/{id}/turns` referencing a removed handler; it now forwards to the enforced operation. Fixed idle WebSocket disconnect cleanup.
- Updated specs, protocol compatibility notes and browser fixtures. No dependencies, inference retries, plugin installs, PR or remote push were added.

VERIFICATION
- `./tools/build-image.sh`: restricted offline Deno TypeScript/build/lint plus 59 frontend tests; 100 backend tests without network/credentials; actual standalone 0.160.0 offline plugin discovery, legacy history and settings acknowledgements for both models, with paid routing/inference mocked.
- `python3 tools/check_browser.py`: shell before delayed history, explicit error/retry, plugin Enter selection/native IDs, edits during send, exact whitespace and failed-draft retention, decoded history/live images, image dialog Escape/focus, one spinner during waiting/streaming, exact context tooltip and phone overflow/navigation. Zero uncaught JavaScript errors.
- `python3 tools/check_browser.py --baseline-bundle tmp/baseline-bundle`: same synthetic transcript/ask at desktop/phone sizes; previous image reproduced three spinners and missing inline images/plugin menu. Before/after PNGs and JSON checks remain in this directory; temporary bundle is removed after validation.
- Live loopback runtime: healthy, 10–21 ms bootstrap (three samples), 13 installed plugins, rooted PNG preview and traversal rejection, canonical/compatibility model bypass rejection, real settings acknowledgements on ephemeral threads. No actual ask dispatched.
- Live production Firefox opened the shell in 483 ms and displayed eight suggestions from the actual installed-plugin catalog, with no overflow or uncaught errors and no submission.
- Actual Uvicorn and WebSocket in an isolated offline runtime: client close followed by graceful shutdown in 0.165 seconds. Installed Uvicorn re-raises SIGTERM after cleanup; signal exit is expected.
- Current image: `localhost/codex-webui-2:local` / `7fabc199e785847f2c00d7b4e3b61b2707a45f2319e356c490a56c85607add73`, served at http://127.0.0.1:8766.

UNVERIFIED
- Paid Jev/model execution with a real selected plugin, live microphone audio, ARM64, and a full accessibility audit.
- File-ID-only/remote images and sending image attachments remain outside this preview subset.
- Native ephemeral full-history reads are unsupported by 0.160.0; native metadata/settings checks and ordinary durable legacy UI history are verified independently.
