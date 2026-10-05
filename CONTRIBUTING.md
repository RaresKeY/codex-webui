# Contributing

Read `AGENTS.md` and `specs/_readme.md`. Keep source, checks, specs and desired design coherent. Use the existing checkout; PR workflows apply only when requested.

`tools/build-image.sh` runs frontend checks in the restricted Deno tool image, builds the application image, and runs backend tests inside it. For focused frontend work use `python3 tools/frontend.py check`. Browser checks cover desktop, phone, navigation, context, empty chat and failed sends. Keep credentials, Codex state, build outputs and private evidence out of Git.

## Gaps

- Browser checks currently depend on the workstation's Firefox BiDi utility.
