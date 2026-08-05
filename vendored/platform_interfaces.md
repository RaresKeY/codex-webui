# Platform interfaces

The app targets 64-bit Linux `amd64` and `arm64`. Docker/Compose packages it; bind mounts supply Codex state, the absolute identical-path workspace root, and app data. Docker build arguments create the container user with host-selected `PUID:PGID`; Compose runs with the same numeric identity and uses `/data/home` as writable runtime `HOME`. CI exercises native `amd64` and QEMU-emulated `linux/arm64`, including the bundled Codex version and degraded HTTP service; actual target-Pi validation is still required. GitHub Container Registry is an optional distribution interface, not a runtime dependency: GitHub Actions publishes the multi-platform manifest while Compose pulls a selected tag. Package visibility and pull authorization are configured in GitHub Packages; Codex login state stays local in the `${HOME}/.codex` bind mount.

Primary references:

- [Docker Compose](https://docs.docker.com/compose/)
- [Docker multi-platform builds](https://docs.docker.com/build/building/multi-platform/)
- [GitHub: publish Docker images](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images)
- [GitHub Packages access and visibility](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility)
- [Tailscale Serve](https://tailscale.com/kb/1242/tailscale-serve)
- [Tailscale access controls](https://tailscale.com/kb/1018/acls)
- [Google Drive API](https://developers.google.com/drive/api/guides/about-sdk)

Tailscale remains host-side private networking. Drive is a mirror/backup destination, never live-database replication.

## Gaps

- Pin published-image digest/retention and Tailscale compatibility; validate non-1000 UID/GID behavior plus the full image on target Pi OS/`arm64`.
- Define trusted proxy headers, host runner transport, and Drive tool/auth/folder/conflict policy.
