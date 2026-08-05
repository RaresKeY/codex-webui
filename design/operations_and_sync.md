# Operations, updates, and sync design

Current updates use explicit host-side `tools/update.sh`; the in-app endpoint is a disabled-by-default command scaffold. Desired in-app updates explain target revision and migrations, back up, drain runs, apply through a constrained mechanism, and verify health. Never mount the Docker socket just to implement a button; a later helper may expose one allowlisted authenticated operation.

Google Drive mirroring is for repository/docs snapshots and consistent backup artifacts. It is not two-way sync for live SQLite, `~/.codex`, or active workspaces. A manifest records checksums, revision, timestamp, scope, exclusions, and conflicts. Private content is opt-in and encrypted if included.

## Gaps

- Decide release branch/tag/digest policy, constrained updater boundary, rollback, and recovery when UI is unhealthy.
- Define Drive folder authority, conflicts, encryption, retention, and restore verification.
