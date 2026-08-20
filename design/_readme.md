# Design map

`design/` records desired current and future design; it is not proof that a feature exists. Current verified behavior belongs in `specs/`.

| Document | Desired-design ownership |
| --- | --- |
| [product_experience.md](product_experience.md) | Navigation, chat and IDE-style experience |
| [system_architecture.md](system_architecture.md) | Target architecture and evolution |
| [sessions_and_codex.md](sessions_and_codex.md) | Resumability, streaming and host-runner transport |
| [projects_and_data.md](projects_and_data.md) | Organization, lifecycle and portability |
| [workspace_experience.md](workspace_experience.md) | Right-side browser and safe editing evolution |
| [automation_and_images.md](automation_and_images.md) | Scheduled work and image library roadmap |
| [security_and_remote_access.md](security_and_remote_access.md) | Loopback, Tailscale, identity and containment |
| [operations_and_sync.md](operations_and_sync.md) | Requested updates, release images, backups and Drive mirror |

Close design gaps only when decided; move implemented contracts into specs with verification.

## Gaps

- Validate the Mac companion in automated browser/WebRTC flows and decide whether the optional container remains a supported product path.
- Add user-tested interaction and accessibility findings.
