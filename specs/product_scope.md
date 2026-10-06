# Product scope

Codex WebUI 2 is a successor derived from WebUI 1 at `4b995df`, retaining its separate local checkout while taking over the original repository's remotes. It retains native thread continuation, streaming, inline approvals, workspace tools, projects, schedules, images, usage and experimental voice. WebUI 1's tracked source and complete local Git refs are archived externally; its local checkout remains an archival reference.

`frontend/src/App.tsx` and `styles.css` own a single text-labeled sidebar, centered readable transcript, right-aligned user bubbles, quiet model provenance, collapsed command/public-thought disclosures and compact auto-routed composer. The optional context panel starts closed. Below 1000px navigation and context become exclusive drawers. Empty workspaces expose a New chat action; new empty threads expose a welcome message and composer.

Conversation rows stay title-only. `ConversationListItem.tsx` exposes the preview, project name, last-updated label and model through a hover summary and an independent details disclosure. The disclosure is available to keyboard and touch users without opening the conversation; missing project records fall back to the workspace directory name. The selection button also references the details as its accessible description.

Text chat uses Auto Jev selection or an explicitly saved per-chat manual choice, followed by the native acknowledgement and exact-input barriers in `jev_routing.md`. Failed drafts remain editable. IME Enter does not submit during composition. Live/routing state blocks duplicate submit; changing conversation cancels pre-submission work. Projects, schedules, images and voice retain inherited behavior. Browser remains a planned context tool.

The sidebar follows the ChatGPT app hierarchy with compact New chat/Search chats/navigation rows, an expandable project list, quiet single-line chats and a fixed profile row. See `sidebar_navigation.md` for behavior, responsive focus contracts and evidence limits.

## Experimental browser

The experimental Browser context provides a visible agent-controlled page, automatic panel opening and smooth pointer feedback. It is one thread-owned session with view-only page pixels; see [browser_integration.md](browser_integration.md).

## Gaps

- No paid integration or real microphone evidence in this project.
- Scheduled tasks and voice are not automatically routed through Jev.
