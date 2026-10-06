# Jev activity

Owners: `backend/app/jev_activity.py`, `chat_service.py`, `task_router.py`, `database.py`, the bounded activity routes in `main.py`, and `frontend/src/JevActivityPage.tsx`, `jev-activity.ts`, and `jev-activity.css`.

## Behavior

The sidebar's Jev entry opens global WebUI activity, refreshed every five seconds while visible. Expand a record for model and effort, decision probabilities and confidence, classifier input/output tokens, policy, preparation duration, stages, information-needs diagnostics, and native thread/turn identifiers. Older records are available through explicit pagination; refreshing preserves already loaded older pages. Loading, empty, unavailable, and interrupted states are explicit. Manual choices are labeled and do not claim Jev usage.

Automatic text submissions create a record after preflight and before classification. Stages track routing, model acknowledgement, and turn submission. Only a valid native `turn/start` response records a submitted turn. Failed or cancelled preparation is stopped, with its last stage and no invented turn. Classification-only `/route` previews are recorded without Codex execution. Manual submissions record their saved model/effort while skipping Jev. Blocked preflight requests do not imply a classifier call.

`GET /api/jev/activity` reads records in descending integer ID order, using an optional positive `before` cursor and a 1–100 limit (default 50). `GET /api/jev/activity/{id}/turn` reads native history for the recorded thread/turn and returns only identifiers and status. The page's Check actual turn action distinguishes submission from running/completed/interrupted/failed execution. Open chat uses the existing chat surface, loading missing chat metadata when necessary. Neither read action starts inference or reclassifies an ask.

## Persistence

SQLite `jev_activity` stores source, stage, status, timestamps, elapsed preparation time, thread/turn IDs, and a whitelist of validated decision metadata. Prompts, transcripts, file contents, provider bodies, arbitrary decision fields, and error messages are excluded. App startup marks unfinished pending records interrupted; that is not a claim that a dispatched native turn stopped. Permanent chat deletion removes its activity records; archive and project deletion preserve them. Database write failure in this optional metadata path does not convert an acknowledged send to a failure or trigger a retry.

Records begin with this feature. Older turns retain their existing model/effort labels but have no reconstructed classifier probabilities, usage, or source.

## Verification

`backend/tests/test_jev_activity.py` covers successful and stopped sends, classification previews, manual bypass, optional-storage failure, native status reads, deletion, cursor stability across new records, and reopening. Router tests verify strict diagnostic choices and safe metadata. Frontend tests cover read-only requests, state validation, activity merging, and loading/navigation. `tools/check_jev_browser.py` uses the production bundle with synthetic data at desktop/phone widths for details, usage, probabilities, diagnostics, native status, pagination, polling, keyboard/touch navigation, empty/error states, and opening a chat.

## Gaps

- Search/context diagnostics are advisory; no automatic search, project-summary loading, or synchronization is implemented.
- Classifier confidence and preparation benefit remain uncalibrated; verification uses fixtures, not paid inference.
- Native turn status is checked on demand; actual execution token usage is not copied into the activity store.
