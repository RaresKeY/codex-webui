# Workspace and file browser

## Status

Implemented bounded tree/read/write plus read-only Git status.

## Source Sync

- Workspace resolver and Git adapter: `backend/app/workspace.py`.
- HTTP routes: `backend/app/main.py`.
- Browser views: `frontend/src/App.tsx`, `frontend/src/api.ts`, and `frontend/src/types.ts`.
- Boundary coverage: `backend/tests/test_workspace.py`, `backend/tests/test_api.py`, and `frontend/src/api.test.ts`.

## Behavior

Every operation targets the single configured absolute workspace root plus a normalized relative path. Container bootstrap mounts that root at the identical absolute path. API paths reject escape outside the canonical root after symlink resolution.

`backend/app/workspace.py` exposes this single configured root. Tree depth is capped at 5 and each directory at 1,000 children; symlink entries are shown but never traversed. Text read/write defaults to a 2 MiB UTF-8 limit, rejects NUL-detected binary content, and uses `O_NOFOLLOW` for the final write component where available. The React panel provides typed icons, a depth-one bootstrap tree with lazy folder loading, explicit preview failures, and plain-text editing.

Implemented operations are tree, text read, text create/overwrite, and bounded Git status. Changes first discovers a repository below the configured root, disables hooks and filesystem monitoring, then runs a fixed porcelain-v1 status query with NUL-delimited paths, a 2 MiB output cap, and a 1,000-entry result cap. It exposes only added, modified, and deleted presentation states. There is no caller-controlled Git command, staging, commit, rename, delete, upload, watcher, ignore-pattern engine, diff source, or multi-root selector.

## Verification

Workspace tests cover canonical containment, symlink escape, depth/entry/file-size limits, binary rejection, and safe writes. API coverage initializes a real temporary Git repository, verifies modified and untracked status mapping, and rejects repositories outside the configured workspace. Frontend normalization tests preserve path, status, repository root, and truncation metadata.

## Gaps

- Surface save and lazy-load errors consistently; preview failures are already explicit.
- Close the remaining read/write ancestor-component TOCTOU window; final-component `O_NOFOLLOW` alone does not prevent a raced parent symlink.
- Add ignore rules, functional watch, Git diffs/staging, conflict detection, directory pagination, and large-tree tests.
