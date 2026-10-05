# Project launch and creation

The sidebar’s project folders and Manage projects open a project-scoped quick-launch page. A compact folder picker appears above the selected project’s prompt composer and last ten chats. Creating a project selects it for prompting. Sending remains nonblocking and independent of the open-chat surface. New chat remains available without a project, with optional explicit project selection; persisted null project IDs are never replaced with the first project. Assigning No project inside a chat clears its organization metadata without changing its native working directory.

Project creation requires only a name. Folder colors and an optional expandable workspace/description section use the existing project API. Workspace defaults to the configured root and stays inside the backend’s rooted path boundary. Error feedback preserves the form, double submission is synchronously guarded, controls reflect pending state, and dialogs support focus containment, Escape and focus restoration. Projects remain local organizational records; this UI does not synthesize ChatGPT Project instructions, remote files or browser tabs.

Successful routed submissions publish their actual model/effort in quick-launch rows and bottom controls. Thread listing enriches metadata with the latest recorded turn selection in one bounded query for the requested thread IDs. Older/foreign chats without a recorded selection have no invented last-model label. The full composer uses recorded assistant turn provenance or acknowledged submission results, independently of its next-turn manual selection. Mobile shows the label near the controls while keeping touch targets and avoiding horizontal overflow.

Sources: `frontend/src/App.tsx`, `LaunchPad.tsx`, `Composer.tsx`, `api.ts`, `chat-activity.ts`, `backend/app/main.py` and `database.py`. Verification includes project/null-model adapter tests, latest-selection storage/listing tests, exact greeting submissions with/without workspace, and the synthetic Firefox project-launch scenarios in `tools/check_launch_browser.py`.

## Gaps

- No paid Jev comparison is run by routine checks; classifier guidance is verified as payload, with synthetic selections used for execution/UI checks.
- Advanced project settings and remote ChatGPT Project content are outside this local project surface.
