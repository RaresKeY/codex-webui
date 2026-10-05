# Sidebar navigation

`frontend/src/App.tsx::ChatSidebar` and the existing `styles.css` own the ChatGPT-style dark sidebar. It retains Codex branding and existing native chat/project behavior. A compact header exposes search and collapse; New chat remains a text/icon row. A narrow utility rail contains labeled icons for chats, Images, Tasks, workspace files, outputs, changes and terminals. Project rows replace filter chips, with expandable Projects and bounded initial visibility (three, then See more). New project opens the existing creation form; the project overflow opens the management page. Selecting a project expands its nested chats and filters loaded/search chats; selecting it again or the chat section heading clears that filter. All projects remain reachable.

Recents uses single-line titles, quiet selected/hover states and the existing independent details disclosure for preview/project/model metadata. The previous count/sort strip becomes a quiet heading and a sort icon; backend order remains authoritative, and reversing it is local presentation. A single scroll region contains navigation, projects and chats. The fixed profile row opens existing settings and never exposes account identifiers.

The header search icon opens a focused search field. The existing debounced, cancellable search rejects obsolete replies and displays bounded failure feedback while retaining matching loaded chats. Escape closes search and returns focus. Ctrl+K / Cmd+K opens search even when the sidebar is collapsed. Images, Tasks, settings, chat selection and creation retain existing routes.

On narrow screens the sidebar is a drawer with safe-area padding, a backdrop and 44px primary targets. Its background content is inert while open, Tab stays within the drawer, Escape closes it, and focus returns to the opener. Selecting a chat or secondary page closes the drawer. Navigation and the context panel remain mutually exclusive. The existing reduced-motion rule applies.

Verification uses the production bundle in offscreen Firefox via `tools/check_sidebar_browser.py`. Dense synthetic content includes 45 chats, seven projects, long titles and long project names. Matched desktop/phone before/after captures, search states, project filtering, focus, keyboard, touch, navigation and fixed-profile scrolling are recorded in `evidence/ui/sidebar/`.

The October 6 reference pass uses title-first rows, compact desktop spacing, collapsible Pinned, colored project icons and nested chats. Pin/unpin persists through the existing metadata API, waits for success, and reports errors in the row disclosure. Search results can be pinned even when absent from the loaded history. The utility rail opens the existing bounded file explorer, Outputs, Changes and Terminals. The screenshot’s browser tab is a reference detail, not a requested browser integration. No browser pane or browser-tab inventory is added.

Verification for this pass is in `evidence/ui/gallery-sidebar/`, including matched desktop, phone, narrow and landscape captures, pin/unpin and workspace navigation. Native capability evidence was inspected in `codex-rs/app-server/README.md` in a local Codex source checkout and protocol `common.rs`: file read/directory methods and background-terminal methods exist; the companion retains its bounded Python file adapter.

Chat ⋯ menus expose archive and confirmed permanent deletion; Archived chats supports restore and delete. Selected project headers expose confirmed project deletion that preserves chats and files. See `chat_management.md`.

## Gaps

Pixel parity with ChatGPT Work is not claimed. Only existing Codex features are exposed. The sidebar search entry follows the official help description at https://help.openai.com/en/articles/10056348-finding-your-chats-projects-and-files-in-chatgpt; it stays limited to this companion's available chat search. Account-specific ChatGPT destinations and identity are outside the companion's capabilities. Mobile evidence uses Firefox touch emulation; physical iOS Safari remains unverified.
