# Workspace and file browser

## Status

Implemented bounded tree/read/write plus read-only Git status.

## Source Sync

- Workspace resolver and Git adapter: `backend/app/workspace.py`.
- HTTP routes: `backend/app/main.py`.
- Browser views: `frontend/src/WorkspaceFileView.tsx`, `frontend/src/workspace-file-view.css`, `frontend/src/workspace-link.ts`, `frontend/src/MarkdownContent.tsx`, `frontend/src/App.tsx`, `frontend/src/api.ts`, and `frontend/src/types.ts`.
- Boundary coverage: `backend/tests/test_workspace.py`, `backend/tests/test_api.py`, and `frontend/src/api.test.ts`.

## Behavior

Every operation targets the single configured absolute workspace root plus a normalized relative path. Container bootstrap mounts that root at the identical absolute path. API paths reject escape outside the canonical root after symlink resolution. Configured Jev credential files and Codex state directories are also denied, including original host mount paths and symlink aliases. Tree and Git changes omit those entries; ordinary project files remain editable.

`backend/app/workspace.py` exposes this single configured root. Tree depth is capped at 5 and each directory at 1,000 children; symlink entries are shown but never traversed. Text read/write defaults to a 2 MiB UTF-8 limit, rejects NUL-detected binary content, and uses `O_NOFOLLOW` for the final write component where available. Explorer provides a file tab, path breadcrumbs, a plain-text editor with synchronized line numbers (at most 120 visible gutter rows), and a right-side tree with filtering and lazy folder loading. Below 540px the tree moves below the editor so both remain reachable. File-link opening selects Explorer automatically, using the conversation working directory for relative paths. Absolute paths remain subject to the same canonical-root API boundary. HTTP links retain their external-link behavior; anchors, non-file schemes, malformed escapes and control characters are not converted into workspace paths. Modified clicks preserve ordinary browser navigation.

Backend-returned canonical relative paths unify chat-link and tree-entry drafts and selection. Text loads discard stale responses on file/chat changes. Save is explicit (button or Ctrl/Command-S), rejects duplicate in-flight submissions and shows failures without clearing edits. Edits made during a save remain dirty after acknowledgement. Unsaved drafts survive panel/tool/chat changes in app memory and trigger the browser navigation warning; successful saves remove clean draft entries. They do not survive reload. Failed/binary/denied reads expose no editor. Refresh reloads the tree, including opened folder children, without replacing editor drafts. Header Sources/Outputs and context controls expose native hover titles.

Implemented operations are tree, text read, text create/overwrite, and bounded Git status. Changes first discovers a repository below the configured root, disables hooks and filesystem monitoring, then runs a fixed porcelain-v1 status query with NUL-delimited paths, a 2 MiB output cap, and a 1,000-entry result cap. It exposes only added, modified, and deleted presentation states. There is no caller-controlled Git command, staging, commit, rename, delete, upload, watcher, ignore-pattern engine, diff source, or multi-root selector.

## Verification

`frontend/src/workspace-link.test.ts` covers file-link resolution and scheme/control rejection. `tools/check_workspace_browser.py` exercises synthetic desktop and 390/320px file opening, editor/tree/breadcrumbs/line numbers, read/save failures, successful writes and draft retention in offscreen Firefox. See `evidence/ui/file-view/`.

Workspace tests cover canonical containment, symlink escape, depth/entry/file-size limits, binary rejection, and safe writes. API coverage initializes a real temporary Git repository, verifies modified and untracked status mapping, and rejects repositories outside the configured workspace. Frontend normalization tests preserve path, status, repository root, and truncation metadata.

## Gaps

- Changes still uses the legacy preview surface; Explorer surfaces load, folder and save failures.
- No external modification/conflict detection, disk-backed draft recovery, syntax highlighting, multiple simultaneous file tabs, or recursive file search. The filter applies to loaded folders and files.
- Close the remaining read/write ancestor-component TOCTOU window; final-component `O_NOFOLLOW` alone does not prevent a raced parent symlink.
- Add ignore rules, functional watch, Git diffs/staging, conflict detection, directory pagination, and large-tree tests.
