# Codex Web UI

A self-hosted browser interface for Codex CLI on Linux. It is designed to run beside workspaces and Codex state on a Raspberry Pi or another Linux host, with same-device browser access first and Tailscale access later.

Project memory is split deliberately:

- [`specs/`](specs/_readme.md): current implemented behavior and verification.
- [`design/`](design/_readme.md): desired current and future design.
- [`vendored/`](vendored/_readme.md): external interfaces and dependencies. Licenses stay in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

The code is early-stage. Read the specs before treating a screen or endpoint as supported.

## Quick start

Prerequisites: Docker with Compose and at least one workspace directory. An existing host Codex login is reused when its state is file-backed; otherwise authenticate once from the running container.

```bash
./tools/bootstrap.sh
```

Run bootstrap as the non-root user who owns `~/.codex` and the workspaces. It refuses root, copies `.env.example` to `.env` on first run, records that user's `PUID`/`PGID`, creates writable data and Codex-state directories, chooses an absolute workspace root, then starts Compose. The default local image is built from source; a configured remote image is pulled instead. Open `http://127.0.0.1:8765`.

When this repository is directly inside a `RawProjects` directory, bootstrap defaults `CODEX_WORKSPACES` to that parent so sibling projects are available. Otherwise it defaults to the absolute path of this repository's `workspaces/` directory. Override it in `.env` with another absolute host path if needed.

Compose requires `CODEX_WORKSPACES` to be absolute and mounts it at the identical absolute path inside the container. This preserves the working-directory paths stored by host-side Codex sessions:

```yaml
volumes:
  - ${HOME}/.codex:/home/codex/.codex
  - type: bind
    source: ${CODEX_WORKSPACES:?Set CODEX_WORKSPACES to an absolute host path}
    target: ${CODEX_WORKSPACES:?Set CODEX_WORKSPACES to an absolute host path}
```

Do not copy Codex credentials into an image or commit them. Compose mounts the host user's `~/.codex` at `/home/codex/.codex`, so a normal host-side Codex login is reused when it is stored there. If that login is keyring-only, or no login exists yet, complete the normal headless device-auth flow inside the running container:

```bash
docker compose exec web codex login --device-auth
docker compose restart web
```

The credentials are written through the mounted `~/.codex` directory and survive container replacement. The MVP runs `codex app-server` inside the web container. Codex therefore sees the container toolchain and mounted files, not arbitrary host-installed programs such as Godot or host compilers.

## Raspberry Pi and updates

The target is a 64-bit `arm64` Linux distribution. CI cross-builds the `linux/arm64` image and smoke-tests it under QEMU, including the bundled Codex version, but this initial slice has not yet been exercised on the target Pi hardware. Install Docker and use Compose as above; authenticate on the host or directly in the container. Tailscale stays outside the app container; keep the direct port loopback-bound and add authenticated Tailscale Serve or a hardened proxy only after the security gaps are closed.

Updates are explicit and user-requested:

```bash
./tools/update.sh
```

`tools/update.sh` is the supported update path. It rebuilds the default local image or pulls the configured prebuilt image, then replaces the service. Back up application data and stop active sessions before migrations. The UI must not silently self-update.

## Prebuilt container image

After the AMD64 and ARM64 smoke jobs pass for `main`, CI builds and publishes a multi-platform image from that same commit at `ghcr.io/rareskey/codex-webui`. The workflow creates mutable `latest` and source-traceable `sha-<commit>` tags; it never pushes an image from a pull request. A newer run cancels an older run for the same branch so an older commit cannot overwrite `latest` afterward.

The first package is private by default. For ordinary Pi pulls without registry credentials, open **Packages → codex-webui → Package settings → Change visibility** and make it public. This is the only GitHub package setting needed for anonymous pulls; private pulls require registry authentication with package-read access. Making a package public cannot be undone.

To use the prebuilt image on a new checkout, copy `.env.example` to `.env`, set `PUID`, `PGID`, and an absolute `CODEX_WORKSPACES` path for the non-root workspace owner, then select the package:

```dotenv
CODEX_WEBUI_IMAGE=ghcr.io/rareskey/codex-webui
CODEX_WEBUI_IMAGE_TAG=latest
```

Run the normal bootstrap; it detects the remote image and starts it without a local build:

```bash
./tools/bootstrap.sh
```

`latest` follows the newest successful `main` build. For a source-traceable deployment, use the `sha-...` tag shown on the package; only a manifest digest is immutable. `tools/update.sh` subsequently pulls the selected remote tag. The Compose mounts, Codex login flow, absolute workspace-path requirement, and loopback-only port binding are unchanged.

## Development and security

Follow [`AGENTS.md`](AGENTS.md) and [`CONTRIBUTING.md`](CONTRIBUTING.md). This app can execute Codex against mounted workspaces, so access is equivalent to the container's authority over those mounts. Read [`SECURITY.md`](SECURITY.md) before remote exposure.

## Gaps

- Project edit/delete, task edit/delete/history, richer image metadata, and advanced runtime/settings management remain future work.
- Host-toolchain execution needs the authenticated external App Server transport described in design; it is not an MVP feature.
- Remote authentication, rate limiting, backup automation, and in-app updates remain staged work; use `tools/update.sh` for updates.
- Establish versioned release tags, digest pinning, package retention, and rollback guidance for published images.
