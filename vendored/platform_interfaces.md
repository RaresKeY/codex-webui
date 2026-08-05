# Platform interfaces

The app targets 64-bit Linux `amd64` and `arm64`. Docker/Compose packages it; bind mounts supply Codex state, the absolute identical-path workspace root, and app data. Docker build arguments create the container user with host-selected `PUID:PGID`; Compose runs with the same numeric identity and uses `/data/home` as writable runtime `HOME`. This is exercised by CI on `amd64` but still needs target-Pi validation.

Primary references:

- [Docker Compose](https://docs.docker.com/compose/)
- [Docker multi-platform builds](https://docs.docker.com/build/building/multi-platform/)
- [Tailscale Serve](https://tailscale.com/kb/1242/tailscale-serve)
- [Tailscale access controls](https://tailscale.com/kb/1018/acls)
- [Google Drive API](https://developers.google.com/drive/api/guides/about-sdk)

Tailscale remains host-side private networking. Drive is a mirror/backup destination, never live-database replication.

## Gaps

- Pin image/Tailscale compatibility and validate UID/GID plus the full image on the target Pi OS/`arm64`.
- Define trusted proxy headers, host runner transport, and Drive tool/auth/folder/conflict policy.
