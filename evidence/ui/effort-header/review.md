# Effort and CLI mentions follow-up — 2026-10-06

VERDICT: APPROVE for the reviewed local UI, event cleanup and runtime image.

## Scope

Reviewed the conversation header and per-reply provenance, combined skill/plugin/app/file mention menu, insertion caret, global and per-chat event cleanup, and the deployed production bundle. Existing quiet styling, manual settings, sidebar, exact prompt preservation, Auto routing barriers, image previews, one message activity indicator and context totals are retained. Starting pending work was preserved in the normal checkout.

## Findings and changes

1. `frontend/src/App.tsx::ChatSurface` forgot the Auto header's model and effort after reopening, despite recorded reply provenance. It now restores the latest reply's recorded selection; a new routing decision or saved manual choice takes precedence. New chats and unrecorded effort remain explicit rather than inferred. The old production bundle fails the added reopening assertion; matched `before/desktop-restored-effort.png` and `after/desktop-restored-effort.png` show the change.
2. `frontend/src/Composer.tsx::choose` deferred caret restoration to an animation frame. Holding that frame while typing reproduced reversed characters after a mention. Caret restoration now runs in the insertion's layout commit; the same keyboard sequence passes with frames held. `caret-before/failure.png` records the reproduction.
3. `backend/app/main.py::events` waited only for native output and retained an idle subscription after disconnect. The global and per-chat sockets now share forwarding/disconnect cleanup. The new global regression failed before patching; both mock and real loopback socket checks pass afterward, with no residual subscribers or server tasks.

The browser fixtures now return valid permission/execution settings and assert the current 280 px sidebar contract. Manual-header assertions cover saved effort after reload and precedence over historical effort. No actionable finding remains in this reviewed scope.

## Verification

- `./tools/build-image.sh`: production TypeScript/build/lint, **70 frontend tests**, **142 backend tests**, and the packaged native offline lifecycle passed. Runtime tests had network disabled and no credential mounts; the socket integration tests used only container loopback. Native checks used disposable state and replaced only paid routing/inference transports with fixtures.
- `python3 tools/check_browser.py --output-dir evidence/ui/effort-header/after`: production Firefox at **1440×1000** and **390×844** passed with zero uncaught JavaScript errors and no horizontal overflow. Includes all four mention selections, delayed-frame typing, exact padded asks, distinct historical/live efforts, reopening, unknown effort, new-chat reset, drafts, images, activity, context and error recovery. `after/checks.json` records the checks.
- `python3 tools/check_permissions_browser.py --output-dir evidence/ui/effort-header/manual`: desktop, **390×844** and **320×640** checks passed for keyboard/touch, saved model/effort, header precedence, acknowledgement gates, rejected changes, drafts and active-turn disabling. No prompt was submitted. `manual/checks.json` records the checks.
- Live native read-only discovery found **53 skills, 13 plugins and 16 apps**, with no category errors. Native offline fixtures also verified rooted fuzzy file search and skill/plugin/app catalog contracts.
- `git diff --check`: passed. Matched desktop before/after, visible phone header, unknown effort and menu screenshots were visually inspected.

## Runtime

The retained local image is `localhost/codex-webui-2:local`, SHA-256 `2c9f108fa2b9118a4cfc6e3ce0123cf5912b913d59bedbf738d29ef2a6714716`. The running container uses that image, and its packaged backend matches the checkout. The launcher preserved existing state, loopback publishing and private Tailscale settings. HTTP and certificate-validated private HTTPS health returned healthy Codex/database state. Deployment preflight found no active native turns.

Offscreen Firefox checked the actual private HTTPS URL at 1440×1000, 390×844 and 320×640. It observed a secure context and healthy WSS, a live skill/plugin/app menu, successful `$ui-polish` insertion, no horizontal overflow, zero uncaught JavaScript errors and **zero HTTP mutations**. Only aggregate results were retained in `live.json`; no real transcript screenshots or prompt output were saved. `runtime.json` records the matching final image/backend and health.

The first replaced container exceeded its 15-second stop grace. Its replacement stopped in 0.38 seconds before deploying the event-cleanup image. This timing alone does not attribute the older timeout to the reproduced global socket leak.

## Unverified

Paid Jev/Codex inference, actual skill/plugin/app execution, full CLI feature parity, live microphone/audio, physical touch devices, a full accessibility audit and ARM64. Old/native external turns lack recorded effort; selection retention/fork copying remain documented gaps. No source publication or PR workflow was requested.
