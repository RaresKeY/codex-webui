# Chat management review — 2026-10-06

Reviewed native lifecycle acknowledgement, active/pending-turn exclusion, exact thread ID forwarding, metadata cleanup, project foreign-key behavior, confirmation focus/cancellation, duplicate submissions, restored metadata, history/search races and narrow layouts. Patched chat-menu closure before deletion confirmation, synchronous action guarding, and stale cached project membership.

Backend tests cover native method selection, unavailable/active/pending behavior through existing leases, malformed acknowledgements, restoration metadata and root-only cleanup, and workspace preservation on project deletion. Offline installed App Server checks use a disposable Codex home and no network/inference. Firefox synthetic lifecycle checks and existing sidebar checks exercise actual production assets, errors/cancellation, reload, desktop, 390px and 320px. No user chat/project was changed during testing.

No remaining actionable findings in this scope. Native external-client concurrency and descendant/external SQL preference pruning remain explicitly documented limits in `specs/chat_management.md`. No claim of bulk management, undelete or paid execution verification.
