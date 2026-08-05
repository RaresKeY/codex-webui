# Persistence model

The app database stores organizational and lifecycle state; mounted `~/.codex` remains authoritative for Codex threads; workspace files and original external images remain filesystem-owned.

`backend/app/database.py` creates four SQLite tables: `projects` with a validated workspace-relative path, `chat_metadata` keyed by Codex thread ID, `settings`, and `scheduled_tasks`. It enables WAL and foreign keys and opens a connection per operation. Initialization migrates older project tables by adding `workspace TEXT NOT NULL DEFAULT '.'` when absent. Codex owns thread/transcript state; workspace and image files are filesystem-owned. There are no local Conversation, Run, Message/event, Task execution, or Image metadata tables.

SQLite is suitable for the one-service deployment. Current initialization uses idempotent DDL plus the one project-workspace compatibility migration, not a versioned migration system or migration lock. Deleting app metadata does not purge Codex or workspace files.

## Gaps

- Add versioned migrations, backup/rollback, busy timeout, indexes, retention, and corruption recovery.
- Add first-class execution/image records only when their lifecycle is implemented; do not duplicate Codex authority casually.
