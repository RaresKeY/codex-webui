# Workspace experience design

The right panel should orient without competing with chat. The MVP lazily expands folders, uses recognizable file-type icons, shows bounded UTF-8 previews with explicit failures, permits plain-text editing, and shows a bounded read-only Git status list for the selected workspace. Desired evolution remembers state per conversation, highlights referenced/changed files, and adds syntax highlighting, safe image previews, diffs, and explicit truncation controls.

Later work may add search, Git diffs/staging, conflict-aware editing, uploads, and drag-to-attach. Mutations must be visibly workspace-scoped, conflict-aware, and reversible or confirmed. External symlinks, hidden/ignored trees, large files, and unsafe types receive explicit blocked states.

## Gaps

- Decide advanced edit scope and whether a heavy editor is justified on the Pi beyond the current textarea.
- Design conflicts between browser, Codex, Git, and external tools; define search, ignore, diff, and icon choices.
