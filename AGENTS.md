# Agent instructions

These instructions apply to the whole repository.

## Project memory first

1. Read `specs/_readme.md` and every spec related to the files you will change.
2. Read matching `design/` documents for product or architecture decisions.
3. Read `vendored/_readme.md` and the relevant external-interface note before changing a dependency or Codex integration.
4. Treat code and tests as evidence. Update a stale spec in the same coherent change.

`specs/` records current intent and implementation: behavior, contracts, boundaries, ownership, and verification. `design/` records desired current and future design. `vendored/` records external dependencies and interfaces; it contains project-authored notes, not copied source or license texts.

Every substantive document in those directories needs a `## Gaps` section. In specs, list current shortfalls or missing evidence. In design, list unresolved desired-design questions or remaining work. In vendored notes, list unpinned versions, compatibility risks, and upstream unknowns. Keep each `_readme.md` map current.

## Engineering approach

- Prototype orchestration in Python; optimize only measured hot paths in native code: Python for glue, C for guts.
- Native work needs a benchmark, boundary, fallback, and build/test plan.
- Keep Codex behind a narrow adapter. UI and persistence must not depend on raw subprocess events.
- Keep filesystem access rooted in configured workspaces; reject traversal and symlink escape.
- Never log prompts, outputs, file contents, environment values, or Codex auth material by default.
- The MVP Codex process runs in the container. Never imply access to unmounted host tools.

## Change discipline

- Make coherent, reviewable commits; do not mix unrelated cleanup.
- Update specs, design gaps, dependency notes, and tests with behavior changes.
- Preserve dirty worktrees and avoid destructive Git operations without explicit approval.
- Schema changes require migration and rollback notes.
- Validate `linux/amd64` and `linux/arm64` for container/native changes.
- Do not add a project license unless the owner explicitly requests one.
- Keep third-party notices at root in `THIRD_PARTY_NOTICES.md`.

Run `./tools/validate.sh` for backend pytest, a clean frontend install/build, lint, and frontend unit tests. Visible changes also need desktop and narrow-width browser checks. Container/deployment changes need a Compose or image-build/runtime check. Codex changes need adapter tests and a redacted smoke run. Report results, omitted checks, affected specs, and remaining gaps.

## Gaps

- Add browser automation, real WebRTC audio evidence, target-Pi hardware, versioned release promotion, and versioned migration commands. The live Codex smoke is opt-in at `tools/smoke_app_server.py`.
