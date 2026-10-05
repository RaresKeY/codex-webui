# Product scope

Codex WebUI 2 is a separate successor project derived from `../codex-webui` at `4b995df`. It retains native thread continuation, streaming, inline approvals, workspace tools, projects, schedules, images, usage and experimental voice. The original project remains unchanged.

`frontend/src/App.tsx` and `styles.css` own a single text-labeled sidebar, centered readable transcript, right-aligned user bubbles, quiet model provenance, collapsed command/public-thought disclosures and compact auto-routed composer. The optional context panel starts closed. Below 1000px navigation and context become exclusive drawers. Empty workspaces expose a New chat action; new empty threads expose a welcome message and composer.

Every text chat ask uses the ordered Jev flow in `jev_routing.md`. Failed drafts remain editable. IME Enter does not submit during composition. Live/routing state blocks duplicate submit; changing conversation cancels pre-submission work. Projects, schedules, images and voice retain inherited behavior. Browser remains a planned context tool.

## Gaps

- No paid integration or real microphone evidence in this project.
- Scheduled tasks and voice are not automatically routed through Jev.
