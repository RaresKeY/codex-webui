# Jev activity

Owners: `backend/app/jev_activity.py`, `chat_service.py`, `task_router.py`, `database.py`, the bounded activity routes in `main.py`, and `frontend/src/JevContext.tsx`, `jev-activity.ts`, and `jev-activity.css`.

## Behavior

Jev is a context sidebar for the selected chat, available only from its sidebar tab. Responses contain no Jev process link or separate routing row. Runs display oldest to newest, with new records appended at the bottom and older paginated runs inserted above. Every row starts collapsed and expands only manually; stage updates preserve its disclosure state. The arrow points right when closed and down when open. Records expand manually in the sidebar; earlier turns have no reconstructed records.

Effort probability rows have a fixed top-to-bottom order: max, xhigh, high, medium, low (lowest effort at the bottom), independent of payload key order. Model probabilities retain their supplied order.

The process shows routing → native model acknowledgement → turn submission, alongside model/effort, decision probabilities and confidence, classifier token usage, policy, duration, information-needs diagnostics and native identifiers. It does not claim that advisory search/context diagnostics execute preparation. The sidebar begins collapsed and opens explicitly from navigation. Selection and records belong to their chat; switching chats does not reuse another chat’s details.

`webui/jevActivity` publishes bounded metadata after record creation and every actual preparation stage change. The existing activity socket carries these events without transcript deltas; they update the matching chat’s cached records directly. There is no five-second history refresh. History loads on chat selection or socket reconnect, with explicit reload and older-page pagination. Hydration merges by ID and timestamp, preserving newer stage events and loaded older pages. Loading, empty, read failure, stopped and interrupted states remain explicit.

Automatic text submissions create a record after preflight and before classification. Stages track routing, model acknowledgement, and turn submission. Only a valid native `turn/start` response records a submitted turn. Failed or cancelled preparation is stopped, with its last stage and no invented turn. Classification-only `/route` previews are recorded without Codex execution. Manual submissions record their saved model/effort while skipping Jev. Blocked preflight requests do not imply a classifier call.

`GET /api/threads/{thread_id}/jev/activity` reads only that chat’s attempts, excluding classification-only previews. `GET /api/jev/activity` remains a compatible global read endpoint and reads records in descending integer ID order, using an optional positive `before` cursor and a 1–100 limit (default 50). `GET /api/jev/activity/{id}/turn` reads native history for the recorded thread/turn and returns only identifiers and status. The sidebar's Check actual turn action distinguishes submission from running/completed/interrupted/failed execution. Neither read action starts inference or reclassifies an ask.

## Persistence

SQLite `jev_activity` stores source, stage, status, timestamps, elapsed preparation time, thread/turn IDs, and a whitelist of validated decision metadata. Prompts, transcripts, file contents, provider bodies, arbitrary decision fields, and error messages are excluded. App startup marks unfinished pending records interrupted; that is not a claim that a dispatched native turn stopped. Permanent chat deletion removes its activity records; archive and project deletion preserve them. Database write failure in this optional metadata path does not convert an acknowledged send to a failure or trigger a retry.

Records begin with this feature. Older turns retain their existing model/effort labels but have no reconstructed classifier probabilities, usage, or source.

## Verification

`backend/tests/test_jev_activity.py` covers successful and stopped sends, classification previews, manual bypass, optional-storage failure, native status reads, deletion, cursor stability across new records, and reopening. Router tests verify strict diagnostic choices and safe metadata. Frontend tests cover read-only requests, state validation, activity merging, and loading/navigation. `tools/check_jev_browser.py` uses the production bundle with synthetic data at desktop/phone widths for turn-linked details, stage flow, usage/probabilities, diagnostics, native status, pagination, absence of five-second polling, direct event updates, chat isolation, narrow-width fit, and error/reload states.

## Migration and rollback

This change reuses the local main’s `jev_activity` table without adding columns or changing stored decision metadata. Initialization creates it idempotently for older deployments. Earlier turns are not backfilled. Rolling back to an image without Jev leaves the optional table unused; preserve it and the existing data volume rather than deleting records. Live event queues have no replay; selecting/reconnecting reloads stored final state.

## Gaps

- Search/context diagnostics are advisory; no automatic search, project-summary loading, or synchronization is implemented.
- Classifier confidence and preparation benefit remain uncalibrated; verification uses fixtures, not paid inference.
- Native turn status is checked on demand; actual execution token usage is not copied into the activity store.
