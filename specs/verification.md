# Verification

Current validation entrypoint is `./tools/validate.sh`: backend pytest, clean frontend `npm ci`, TypeScript/Vite build, frontend lint, and Vitest. The final local implementation pass records 27 passing backend tests and five passing frontend tests covering authoritative history/status, command/file normalization, streamed deltas/context usage, nested usage without invented values, and approval failure remaining pending/retryable. CI runs backend tests plus frontend build/lint/test, builds and loads native `amd64` and QEMU-emulated `linux/arm64` containers, verifies non-root identity, writable `HOME`, and the pinned bundled Codex version, then smoke-tests the degraded HTTP service on both architectures. Only a successful `main` push can reach the dependent publishing job; pull requests never receive package-write permission or push images. The publisher rebuilds that commit into one multi-platform GHCR manifest with `latest` and commit-derived tags, and ref-scoped concurrency prevents stale runs from publishing afterward. Backend tests cover projects/workspace migration, settings/thread metadata, scheduler completion and in-process leases, update gating, authoritative search/recency parameters, approval lifecycle and current-time handling, protocol bounds, security origins/headers, event scoping, configuration enums, and workspace traversal/symlinks.

Tests never use a developer's real `~/.codex`, workspaces, credentials, or conversations. A release record includes revision, locks, schema, Codex compatibility, commands/results, platform, known gaps, and a redacted smoke result.

## Gaps

- Expand frontend unit coverage and add browser tests, image endpoint tests, updater tests, versioned migration/rollback tests, and adversarial ancestor-race tests.
- Establish live Codex opt-in tests, target-Pi hardware run evidence beyond QEMU, and performance budgets.
- Add a registry-manifest check for both platform descriptors and expected OCI source/revision labels.
