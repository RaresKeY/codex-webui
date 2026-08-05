# Contributing

Start with `AGENTS.md`, then follow `specs/_readme.md`. Use a focused branch and keep behavior, tests, and project-memory updates together.

A pull request states the user-visible outcome, trust-boundary or migration impact, checks and results, screenshots for UI changes, updated specs/gaps, and dependency/notice impact. Do not commit secrets, local Codex state, generated databases, workspace contents, or private images.

Run `./tools/validate.sh` before review. UI changes also need manual browser evidence until browser automation is added.

## Gaps

- Add browser-evidence and local container-smoke commands plus maintainer/reviewer ownership.
