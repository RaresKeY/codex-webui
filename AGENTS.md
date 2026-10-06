# Agent instructions

Read `specs/_readme.md` and relevant specs, design and vendored notes first. Keep them synchronized with behavior. Every substantive document in those directories needs a `## Gaps` section.

Work in this project's normal checkout, preserve dirty work, and follow the user's workstation branch policy. Do not create PRs unless requested. Do not add a license. Keep the primary icon at root (`icon.png`); third-party notices belong at root.

Python owns orchestration, HTTP, persistence and the Jev boundary. React/TypeScript owns presentation. Keep Codex behind the existing narrow App Server adapter. Workspace paths must remain rooted and reject traversal/symlink escape. Do not log prompts, outputs, files, keys, environment values or auth material. Credentials and Codex state remain external to images.

Text chat in Auto follows Jev selection → acknowledged model change → unchanged user ask. The user explicitly authorized per-chat manual model/effort selection on 2026-10-05; manual selection skips Jev but retains the acknowledgement and unchanged-ask barriers. This ordering belongs to `backend/app/chat_service.py`, independently of the frontend. Keep both `/messages` and the `/turns` alias routed; reject execution model/effort overrides and thread-start prompts. Require the actual `thread/settings/update` acknowledgement; metadata reads cannot substitute for it. Preserve the two-model policy and the user-directed WebUI learning/teaching preference for Sol 6.1, strict typed validation, exact input whitespace and no automatic retries. Do not alter historical task-router experiments or execute classified tasks while testing the router. Paid integration smokes require an explicit request.

Use `tools/frontend.py` for frontend dependency installation and Deno build/lint/test execution in restricted non-root containers. Download dependencies only when explicitly authorized (`--fetch`), use the existing lockfile and never invoke host Node/npm-family tooling. Runtime images are built with `tools/build-image.sh`; run them with `tools/run-container.sh`. Keep credentials out of build contexts. Local artifacts are ephemeral; retain the requested current image.

## Podman retention and cleanup

Follow the global Podman retention rule and `specs/deployment_operations.md`. Keep the deployed runtime, the current frontend toolchain, an active deployment candidate, and one verified previous runtime under `localhost/codex-webui-2:rollback`. Older `before-*` snapshots and superseded untagged project runtimes are obsolete after a successful deployment unless the user explicitly requires another recovery image.

Final images must explicitly carry `io.rareskey.retention=retain|ephemeral`, `io.rareskey.project=codex-webui-2`, and an appropriate purpose label; build intermediates carry the ephemeral and project labels. `tools/build-image.sh` holds the shared workstation build-retention lock throughout the build. Cleanup takes the exclusive lock, verifies no uncoordinated build is active, checks exact ownership and retention labels, all container references, image dependencies and ongoing-task needs, and removes only reviewed exact IDs. Keep the parent-image closure of retained images. Do not treat the absence of a container as proof that another project's image is disposable.

Use the prescribed wrappers and `--rm` for disposable containers. Once the candidate is deployed and verified, rotate the single rollback image and remove obsolete project images/intermediates and generated local outputs. Preserve running services, retained toolchains, unrelated/unreviewed images, persistent volumes, credentials, the browser profile, source and user evidence. Never use unrestricted system/image prune, volume pruning, `--external`, forced deletion or manual container-storage deletion. Weekly automatic pruning covers only explicitly ephemeral dangling images older than seven days; tagged and unlabeled images require separate review.

## Verification

Run backend tests, frontend build/lint/unit tests, and desktop/narrow-width browser checks for behavioral and visible changes. Image changes need a build and runtime check. Validate each architecture actually claimed as supported; the current local image is amd64 and ARM64 remains unverified. Codex protocol changes require adapter tests and schema inspection; live model execution is opt-in. Report omitted checks candidly.

## Source and evidence privacy

Committed source and evidence must use generic user icons and portable paths. Keep private hostnames, personal machine/user details, private hosting and backup arrangements, credentials and real transcripts out of public source and captures. Runtime discovery may resolve private access locally without storing addresses in committed reports.

## Gaps

- Add portable browser automation and live microphone evidence; current browser-check tooling uses the workstation Firefox BiDi client.
