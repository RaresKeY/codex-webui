# Verification

`tools/build-image.sh` verifies the frontend with `tools/frontend.py check`, builds the runtime image, and runs `backend/tests` plus `tools/check_thread_lifecycle.py` in that image without network or credentials. The native lifecycle check uses temporary Codex state and exercises new-thread creation, metadata/history hydration and acknowledged settings changes for both models. Its complete routed-send check leaves those native calls intact and replaces only paid Jev/inference transports with fixtures. `tools/validate.sh` also supports focused host Python tests plus the same container frontend checks. Python and JavaScript locks record the tested dependency graph.

Backend coverage includes inherited native threads, provisional continuation, approvals, realtime capability, Host/Origin/workspace bounds, scheduling and persistence. Jev tests verify typed decisions, inconsistent choices, finite values, prompt isolation, credential handling, fail-closed errors and no retries. Direct chat tests cover both message URLs, rejected caller model/effort, rejected thread-start prompts/steering, exact padded Unicode input, native loading/settings ordering, delayed/failed acknowledgements, streamed errors and cancellation/concurrency. Frontend coverage includes inherited normalization, lifecycle/model provenance, Markdown safety, realtime setup and grouped commands, plus single-request streamed submission and failure barriers.

Visible acceptance checks run the actual production bundle in headless Firefox at desktop and narrow widths: one sidebar, readable transcript/composer, empty/new chat, exclusive drawers, collapsed command/thought details, keyboard Enter/Shift+Enter, retained draft on failure, and reachable secondary pages. `tools/check_browser.py` records reproducible synthetic browser checks without paid calls or account metadata.

`tools/generate-app-server-schema.sh` generated the public 0.160.0 schema. `ThreadLoadedListResponse.data`, `ThreadSettingsUpdateParams.threadId/model/effort`, its empty-object response, and `TurnStartParams.model/effort/input/threadId` match the adapter. Inherited protocol tests target the adapter subset originally authored for 0.147.0; generated 0.160.0 compatibility does not imply complete protocol coverage.

## Observed results — 2026-10-05

- Frontend TypeScript/production build and lint passed inside the restricted Deno tool container; 59 tests passed across eleven files using permission-preserving fork workers.
- 100 backend tests passed with network disabled and no credential mounts.
- Production Firefox fixture checks passed at 1440×1000 and 390×844 with zero uncaught JavaScript errors. `evidence/ui/checks.json` and matched before/after screenshots record geometry, a single backend send with exact padded text, exact failure-draft retention, navigation and secondary-page checks.
- Chat interaction checks added slow-history shell availability, explicit startup/history retry, plugin keyboard selection and structured mention metadata, edits during acknowledgement, decoded history/live image previews and dialog Escape/focus, a single spinner in waiting/streaming, exact context totals and phone menu overflow. The previous runtime bundle reproduced three message spinners and no inline images or plugin menu.
- The compatibility conversation-turn URL shares the enforced send operation. Idle WebSocket disconnect tests release native subscribers; a real offline Uvicorn/WebSocket check shut down in 0.165 seconds after client close.
- Native plugin discovery passed with disposable state and network disabled; no install or plugin execution was requested.
- A screenshot-reported failure was reproduced in the real 0.160.0 runtime: omitted history mode produced paginated threads, while full read and resume refused `list_turns is not supported yet`. Explicit legacy creation restored the new-thread lifecycle; incompatible existing history gets a bounded recovery message.
- Live production Firefox opened the shell in 483 ms and displayed the installed @ plugin menu without overflow or uncaught JavaScript errors. No message was submitted.
- The current loopback runtime returned shell bootstrap in 10–21 ms across three checks, discovered 13 installed plugins and served the rooted PNG preview. Canonical and compatibility caller-model bypasses remained rejected before routing.
- The rootless runtime served the frontend on loopback with healthy App Server connectivity, database status and availability of both routing models. These read-only checks did not route or execute a real ask.
- The native offline lifecycle check acknowledged settings updates on a fresh loaded thread for both models, then submitted a padded ask through the unified backend operation with only paid transports mocked.
- The rebuilt production container rejected caller model/effort and thread-start prompt bypasses with 422, and acknowledged both model changes on a fresh ephemeral thread without submitting an ask.

## Gaps

- Paid text routing/execution, real plugin execution, microphone audio and ARM64 runtime are unverified.
- The portable browser tool depends on the workstation's existing Firefox BiDi client.
- No browser accessibility audit or task-success calibration is claimed.
