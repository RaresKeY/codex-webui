# Operations and sync

Local rootless Podman images and loopback launch are the supported workflow. Keep credentials/state externally mounted, app data separate, dependency installation reproducible and runtime authority limited to mounted workspaces. Build the current image on demand; do not accumulate archives or publish automatically.

## Gaps

- Remote authentication, image promotion/rollback, ARM64 verification and consistent backups require separate work.
