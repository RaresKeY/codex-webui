# Persistence model

The app database stores organizational and lifecycle state; mounted `~/.codex` remains authoritative for Codex threads; workspace files and original external images remain filesystem-owned.

`backend/app/database.py` creates five SQLite tables: `projects` with a validated workspace-relative path, `chat_metadata` keyed by Codex thread ID, `turn_selections` keyed by native thread/turn IDs, `settings`, and `scheduled_tasks`. It enables WAL and foreign keys and opens a connection per operation. Initialization migrates older project tables by adding `workspace TEXT NOT NULL DEFAULT '.'` when absent. Codex owns thread/transcript state; workspace and image files are filesystem-owned. There are no local Conversation, Run, Message/event, Task execution, or Image metadata tables.

`turn_selections` stores only acknowledged model and effort after successful WebUI turn creation. It contains no prompts, transcripts, credentials or raw routing payloads. Thread reads enrich matching turns under `webui`; missing rows and failed optional metadata reads stay unknown without hiding native history. SQLite write failure after acknowledgement returns `selectionSaved: false` without falsely reporting failed execution. Reinitialization preserves distinct selections for earlier turns.

SQLite is suitable for the one-service deployment. Current initialization uses idempotent DDL plus the one project-workspace compatibility migration, not a versioned migration system or migration lock. Deleting project/app grouping metadata does not purge Codex or workspace files. Permanent chat deletion uses the native App Server operation before removing the requested root’s app preferences and model selections; see `chat_management.md`.

Per-chat permission preferences use bounded string values in the existing `settings` table under `chat-permissions:<thread-id>`. They are saved only after a native settings acknowledgement and read/reapplied before each interactive text turn, so restarting the app preserves the WebUI choice without relying on native provisional-thread materialization. Other chats and new-chat defaults are independent. See `chat_permissions.md`.

`chat-execution:<thread-id>` stores the explicitly selected Auto/manual model and effort. `new-chat-permissions` records the latest acknowledged explicit permission choice in the same transaction as its per-chat preset. Creation snapshots that preset into the new chat after native creation succeeds; later choices do not mutate existing chats. Model/effort selection defaults to Auto for each new chat and does not inherit.

## Gaps

- Add versioned migrations, backup/rollback, busy timeout, indexes, retention, and corruption recovery.
- Selection rows have no automatic pruning or fork copying; older/native external turns lack recorded effort.
- Add first-class execution/image records only when their lifecycle is implemented; do not duplicate Codex authority casually.
