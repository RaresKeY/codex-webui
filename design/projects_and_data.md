# Projects and data design

Projects are organizational containers, not directories. The MVP stores a validated default workspace and assigns conversations without changing Codex thread IDs. Desired evolution adds broader project defaults and lifecycle controls.

Conversation text search should remain authoritative to Codex where supported; local indexes, if later added, must be transparent and user-controlled. Archive hides records without destroying Codex state. Deletion separates app metadata, app-owned artifacts, upstream state, and workspace files into independently confirmed actions.

Desired portability is a versioned manifest plus selected transcripts/artifacts, excluding secrets and absolute paths. Import detects duplicate thread IDs and missing workspaces. Backups are consistent database snapshots, not copied live files.

## Gaps

- Decide transcript persistence/caching, export schema, import conflicts, retention/trash duration, and secure artifact deletion.
