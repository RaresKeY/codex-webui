# Chat and project management

Chat ⋯ menus open a compact icon popover offering Pin/Unpin, Archive/Restore and Delete when supported. The popover uses the native top layer to avoid sidebar clipping, stays within the viewport, and overlays history without shifting rows. Only one chat action popover is open at a time. Outside pointer input closes it; Escape closes and returns focus to its trigger. A separator groups pinning above lifecycle actions; Delete uses the existing danger token. Project, update, preview and model metadata remain in the row tooltip and accessible description, rather than filling the action menu. Pin and lifecycle writes share a synchronous duplicate-action guard; pending/error states stay visible. Archive removes the chat from active history, pinned lists, search results and the launch page. The sidebar's Archived chats page loads native archived history with explicit pagination; restore retains pins, project membership and recorded model/effort. Selecting an archived title restores and opens it. Failed operations remain visible and are never automatically retried.

Permanent deletion requires a confirmation explaining that native spawned descendant chats are included. Cancel and Escape issue no mutation. Confirmation is guarded synchronously against duplicate submissions. Archive/delete are disabled while the UI knows a turn is running; the backend reserves the thread against pending WebUI sends/settings changes and reads native status before mutation. Native lifecycle notifications reconcile external and descendant changes without exposing transcripts in the activity feed. Excluded IDs prevent stale history/search requests from reintroducing removed chats.

`POST /api/threads/{id}/archive`, `POST /api/threads/{id}/unarchive`, and `DELETE /api/threads/{id}` call the installed App Server's corresponding operations. Archive/delete require the native empty acknowledgement; restore requires a matching returned thread ID. Delete returns 204 and removes root app metadata, turn selections and per-chat preferences after native acknowledgement. The legacy `DELETE /api/conversations/{id}` alias now permanently deletes; use the explicit archive endpoint for reversible removal. Neither routing nor inference runs for these operations. Native Codex owns persisted transcripts and descendant lifecycle; the app does not unlink native files.

Selected projects expose Delete project in the project header's ⋯ menu. Confirmation explains that chats become unassigned and workspace files remain on disk. The existing project DELETE endpoint removes the SQLite grouping; foreign keys clear project assignments while pins, selections, native chats and workspace files survive. UI selection and cached search membership update immediately after acknowledgement.

Source: `backend/app/main.py`, `backend/app/database.py`, `frontend/src/App.tsx`, `frontend/src/ArchivedChats.tsx`, `frontend/src/ConversationListItem.tsx`, `frontend/src/api.ts`.

Verification: `backend/tests/test_chat_lifecycle.py`, frontend notification tests, `tools/check_thread_lifecycle.py` with a disposable offline Codex home, and `tools/check_chat_management_browser.py` with synthetic browser data. The native contract is documented at https://learn.chatgpt.com/docs/app-server.

See [turn_presentation.md](turn_presentation.md) for the pinned Sources/Outputs card, turn work disclosure, hover timestamps and inclusive native response branching with retained selection/preferences copying.

## Gaps

- Native lifecycle operations require native persisted/managed threads; unsupported or rejected native operations show an error rather than pretending to succeed.
- Per-thread WebUI reservations do not serialize unrelated external Codex clients. Native Codex remains responsible for concurrent lifecycle behavior and descendants.
- SQL cleanup explicitly covers the requested deleted root. Stale app metadata for native descendants or externally deleted threads can remain; it contains preferences and model selections, not transcripts.
- No bulk selection, project archiving, automatic retention, or undelete is implemented.
