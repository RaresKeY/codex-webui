# Codex Web UI

A self-hosted browser interface for Codex CLI on Linux. It is designed to run beside workspaces and Codex state on a Raspberry Pi or another Linux host, with same-device browser access first and Tailscale access later.

Project memory is split deliberately:

- [`specs/`](specs/_readme.md): current implemented behavior and verification.
- [`design/`](design/_readme.md): desired current and future design.
- [`vendored/`](vendored/_readme.md): external interfaces and dependencies. Licenses stay in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

The code is early-stage. Read the specs before treating a screen or endpoint as supported.

## Quick start

Prerequisites: Docker with Compose, an existing Codex CLI login on the host, and at least one workspace directory.

```bash
./tools/bootstrap.sh
```

Run bootstrap as the non-root user who owns `~/.codex` and the workspaces. It refuses root, copies `.env.example` to `.env` on first run, records that user's `PUID`/`PGID`, creates the writable `data/home` directory, chooses an absolute workspace root, then builds and starts Compose. Open `http://127.0.0.1:8765`.

When this repository is directly inside a `RawProjects` directory, bootstrap defaults `CODEX_WORKSPACES` to that parent so sibling projects are available. Otherwise it defaults to the absolute path of this repository's `workspaces/` directory. Override it in `.env` with another absolute host path if needed.

Compose requires `CODEX_WORKSPACES` to be absolute and mounts it at the identical absolute path inside the container. This preserves the working-directory paths stored by host-side Codex sessions:

```yaml
volumes:
  - ${HOME}/.codex:/home/codex/.codex
  - type: bind
    source: ${CODEX_WORKSPACES:?Set CODEX_WORKSPACES to an absolute host path}
    target: ${CODEX_WORKSPACES:?Set CODEX_WORKSPACES to an absolute host path}
```

Do not copy Codex credentials into an image or commit them. The MVP runs `codex app-server` inside the web container. Codex therefore sees the container toolchain and mounted files, not arbitrary host-installed programs such as Godot or host compilers.

## Raspberry Pi and updates

The target is a 64-bit `arm64` Linux distribution. CI cross-builds the `linux/arm64` image and smoke-tests it under QEMU, including the bundled Codex version, but this initial slice has not yet been exercised on the target Pi hardware. Install Docker, authenticate Codex once on the host, and use Compose as above. Tailscale stays outside the app container; keep the direct port loopback-bound and add authenticated Tailscale Serve or a hardened proxy only after the security gaps are closed.

Updates are explicit and user-requested:

```bash
./tools/update.sh
```

Back up application data and stop active sessions before migrations. The UI must not silently self-update.

## Development and security

Follow [`AGENTS.md`](AGENTS.md) and [`CONTRIBUTING.md`](CONTRIBUTING.md). This app can execute Codex against mounted workspaces, so access is equivalent to the container's authority over those mounts. Read [`SECURITY.md`](SECURITY.md) before remote exposure.

## Gaps

- Project edit/delete, task edit/delete/history, richer image metadata, and advanced runtime/settings management remain future work.
- Host-toolchain execution needs the authenticated external App Server transport described in design; it is not an MVP feature.
- Remote authentication, rate limiting, backup automation, and in-app updates remain staged work; use `tools/update.sh` for updates.
