# Agent instructions

Read `specs/_readme.md` and relevant specs, design and vendored notes first. Keep them synchronized with behavior. Every substantive document in those directories needs a `## Gaps` section.

Work in this project's normal checkout, preserve dirty work, and follow the user's workstation branch policy. Do not create PRs unless requested. Do not add a license. Keep the primary icon at root (`icon.png`); third-party notices belong at root.

Python owns orchestration, HTTP, persistence and the Jev boundary. React/TypeScript owns presentation. Keep Codex behind the existing narrow App Server adapter. Workspace paths must remain rooted and reject traversal/symlink escape. Do not log prompts, outputs, files, keys, environment values or auth material. Credentials and Codex state remain external to images.

Text chat always follows Jev selection → acknowledged model change → unchanged user ask. This ordering belongs to `backend/app/chat_service.py`, independently of the frontend. Keep both `/messages` and the `/turns` alias routed; reject execution model/effort overrides and thread-start prompts. Require the actual `thread/settings/update` acknowledgement; metadata reads cannot substitute for it. Preserve the two-model V5 policy, strict typed validation, exact input whitespace and no automatic retries. Do not alter historical task-router experiments or execute classified tasks while testing the router. Paid integration smokes require an explicit request.

Use `tools/frontend.py` for frontend dependency installation and Deno build/lint/test execution in restricted non-root containers. Download dependencies only when explicitly authorized (`--fetch`), use the existing lockfile and never invoke host Node/npm-family tooling. Runtime images are built with `tools/build-image.sh`; run them with `tools/run-container.sh`. Keep credentials out of build contexts. Local artifacts are ephemeral; retain the requested current image.

Run backend tests, frontend build/lint/unit tests, and desktop/narrow-width browser checks for behavioral and visible changes. Image changes need a build and runtime check. Validate each architecture actually claimed as supported; the current local image is amd64 and ARM64 remains unverified. Codex protocol changes require adapter tests and schema inspection; live model execution is opt-in. Report omitted checks candidly.

## Gaps

- Add portable browser automation and live microphone evidence; current browser-check tooling uses the workstation Firefox BiDi client.
