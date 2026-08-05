# Operations, updates, and sync design

Current host-side `tools/update.sh` rebuilds the default local image or explicitly pulls a selected GHCR tag and recreates the service without building. The initial distribution channel publishes `latest` and a traceable commit-derived tag after successful `main` CI. Desired release management adds version tags, digest selection, retention, rollback, compatibility notes, and an in-app flow that explains target revision and migrations before invoking a constrained update helper. Never mount the Docker socket just to implement a button; a later helper may expose one allowlisted authenticated operation.

Google Drive mirroring is for repository/docs snapshots and consistent backup artifacts. It is not two-way sync for live SQLite, `~/.codex`, or active workspaces. A manifest records checksums, revision, timestamp, scope, exclusions, and conflicts. Private content is opt-in and encrypted if included.

## Gaps

- Decide immutable version-tag/digest policy, release promotion, rollback, retention, constrained updater boundary, and recovery when UI is unhealthy.
- Define Drive folder authority, conflicts, encryption, retention, and restore verification.
