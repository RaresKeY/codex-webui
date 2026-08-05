# Workspace and file browser

Every operation targets the single configured absolute `CODEX_WORKSPACES` root plus a normalized relative path. Bootstrap mounts that root at the identical absolute path in the container. API paths reject escape outside the canonical root after symlink resolution.

`backend/app/workspace.py` exposes this single configured root. Tree depth is capped at 5 and each directory at 1,000 children; symlink entries are shown but never traversed. Text read/write defaults to a 2 MiB UTF-8 limit, rejects NUL-detected binary content, and uses `O_NOFOLLOW` for the final write component where available. The React panel provides typed icons, a depth-one bootstrap tree with lazy folder loading, explicit preview failures, and plain-text editing.

Implemented operations are tree, text read, and text create/overwrite. There is no rename, delete, upload, watcher, ignore-pattern engine, Git status source, or multi-root selector. Current frontend Git/change labels are presentation scaffolding rather than backend-derived status.

## Gaps

- Surface save and lazy-load errors consistently; preview failures are already explicit.
- Close the remaining read/write ancestor-component TOCTOU window; final-component `O_NOFOLLOW` alone does not prevent a raced parent symlink.
- Add ignore rules, functional refresh/watch and Git status, conflict detection, directory pagination, and large-tree tests.
