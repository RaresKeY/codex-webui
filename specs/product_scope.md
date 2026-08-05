# Product scope

Codex Web UI is a single-operator, self-hosted browser interface for Codex on Linux. The first deployment is same-device loopback access. It organizes local Codex conversations into projects and connects each conversation to one configured workspace.

The React frontend implements the three-pane shell and project, schedule, image, and settings screens in `frontend/src/App.tsx`. `frontend/src/api.ts` adapts canonical backend responses into UI types. Live behavior includes project creation and conversation assignment; authoritative debounced conversation search with recency sorting; thread history/resume/turns; delta and context-usage merging; pending approvals; lazy workspace browsing and text editing; task creation/toggle/run-now; image import/list/search/delete; and nested usage display. Approval cards enter a sending state and resolve only after the backend accepts the response; a failed POST leaves the request pending, shows an error, and allows retry. Demo data is used only when initial bootstrap establishes demo mode; live history/file failures show error states.

The FastAPI backend currently provides health/bootstrap, Codex threads/turns/resume/fork/archive, WebSocket events, pending approvals, account/models/usage, project metadata, settings, workspace tree/read/write, PNG/JPEG/GIF/WebP upload/list/delete, UTC interval/cron tasks, and a gated update-command endpoint. Current source is `backend/app/main.py` with focused services in the adjacent modules.

Codex remains authoritative for execution and native conversation continuation. SQLite stores projects with validated workspace-relative roots, thread-to-project/pin metadata, settings, and schedules. Images are app-owned files; interactive transcripts/runs remain Codex-owned. Transcript replay must never masquerade as resumption.

Bootstrap non-goals include public hosting, multi-user collaboration, replacing Codex auth/policy, unrestricted terminal access, two-way cloud conflict resolution, and silent self-update.

## Gaps

- Project edit/delete, schedule edit/delete/history, image metadata/tags, and settings reconnect/diagnostics/export remain incomplete.
- Authentication, remote multi-user semantics, project portability, and browser-level accessibility evidence remain incomplete.
