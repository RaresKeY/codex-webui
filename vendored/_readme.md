# External interface and dependency map

`vendored/` contains project-authored notes about external software. It is not copied source or a license directory; notices belong in root `THIRD_PARTY_NOTICES.md`.

| Document | External ownership |
| --- | --- |
| [codex_cli_app_server.md](codex_cli_app_server.md) | Codex CLI/App Server compatibility |
| [jev_browser.md](jev_browser.md) | Local Jev port and Chromium Flatpak/CDP boundary |
| [runtime_dependencies.md](runtime_dependencies.md) | Runtime/build dependency policy |
| [platform_interfaces.md](platform_interfaces.md) | Docker, GHCR, Linux/Pi, Tailscale and Drive |

Exact resolved versions come from lockfiles/image digests. Record the upstream primary source, use case, license identifier, and internal owning adapter.

## Gaps

- Generate the complete transitive dependency/version/license inventory and automated drift/notices checks from release locks and images.

[jev_task_router.md](jev_task_router.md) records the owning router policy snapshot and interactive transport boundary.
