# Workspace experience design

The right panel should orient without competing with chat, so it starts collapsed and opens when requested or when agent browser activity needs to be visible. The experimental Browser should feel like the reference ChatGPT split view: a wide right panel, page title/address/navigation chrome, and a smoothly moving agent cursor. Narrow screens use the existing mutually exclusive drawer contract. The MVP lazily expands folders, uses recognizable file-type icons, shows bounded UTF-8 previews with explicit failures, permits plain-text editing, and shows a bounded read-only Git status list for the selected workspace. Desired evolution remembers state per conversation, highlights referenced/changed files, and adds syntax highlighting, safe image previews, diffs, and explicit truncation controls.

Later work may add search, Git diffs/staging, conflict-aware editing, uploads, and drag-to-attach. Mutations must be visibly workspace-scoped, conflict-aware, and reversible or confirmed. External symlinks, hidden/ignored trees, large files, and unsafe types receive explicit blocked states.

The requested navigation direction is a ChatGPT app style sidebar adapted to the Codex companion: quiet dark surfaces, icon/text destinations, project rows, title-only chats and bottom-anchored profile settings. Existing Codex features determine available destinations; implemented navigation is documented in `specs/sidebar_navigation.md`.

## Gaps

- Decide advanced edit scope and whether a heavy editor is justified on the Pi beyond the current textarea.
- Design conflicts between browser, Codex, Git, and external tools; define search, ignore, diff, and icon choices.
