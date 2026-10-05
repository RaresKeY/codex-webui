# Verification

`tools/build-image.sh` verifies the frontend with `tools/frontend.py check`, builds the runtime image, and runs `backend/tests` in that image without network or credentials. `tools/validate.sh` also supports focused host Python tests plus the same container frontend checks. Python and JavaScript locks record the tested dependency graph.

Backend coverage includes inherited native threads, provisional continuation, approvals, realtime capability, Host/Origin/workspace bounds, scheduling and persistence. New Jev tests verify typed decisions, inconsistent choices, finite values, prompt isolation, credential handling, fail-closed errors and no retries. Frontend coverage includes inherited normalization, lifecycle/model provenance, Markdown safety, realtime setup and grouped commands, plus explicit awaited route/model-change/turn ordering and failure barriers.

Visible acceptance checks run the actual production bundle in headless Firefox at desktop and narrow widths: one sidebar, readable transcript/composer, empty/new chat, exclusive drawers, collapsed command/thought details, keyboard Enter/Shift+Enter, retained draft on failure, and reachable secondary pages. `tools/check_browser.py` records reproducible synthetic browser checks without paid calls or account metadata.

`tools/generate-app-server-schema.sh` generated the public 0.160.0 schema. The selected `ThreadResumeParams.model` and `TurnStartParams.model/effort/input/threadId` fields match the adapter. Inherited protocol tests target the adapter subset originally authored for 0.147.0; generated 0.160.0 compatibility does not imply complete protocol coverage.

## Observed results — 2026-10-05

- Frontend TypeScript/production build and lint passed inside the restricted Deno tool container; 44 tests passed across nine files using permission-preserving fork workers.
- 60 backend tests passed in the runtime image with network disabled and no credential mounts.
- Production Firefox fixture checks passed at 1440×1000 and 390×844 with zero uncaught JavaScript errors. `evidence/ui/checks.json` and five screenshots record geometry, ordered send, failure retention, navigation and secondary-page checks.
- The rootless runtime served the frontend on loopback with healthy App Server connectivity, database status and availability of both routing models. These read-only checks did not route or execute a real ask.

## Gaps

- Paid text routing/execution, microphone audio and ARM64 runtime are unverified.
- The portable browser tool depends on the workstation's existing Firefox BiDi client.
- No browser accessibility audit or task-success calibration is claimed.
