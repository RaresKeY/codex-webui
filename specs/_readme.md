# Specifications map

`specs/` is committed project memory for current ground truth. Describe only behavior supported by code and verification. Desired behavior belongs in `design/`.

| Document | Status | Ground-truth ownership |
| --- | --- | --- |
| [product_scope.md](product_scope.md) | Partial MVP | User roles, milestone surface, projects and chats |
| [architecture.md](architecture.md) | Partial MVP | Components, boundaries, flow and source ownership |
| [codex_app_server.md](codex_app_server.md) | Partial MVP | Containerized Codex adapter and resumable sessions |
| [persistence_model.md](persistence_model.md) | Implemented subset | Records, identifiers, migrations and retention |
| [workspace_files.md](workspace_files.md) | Implemented subset | Workspace roots, browser and file safety |
| [usage_observability.md](usage_observability.md) | Partial MVP | Context/usage display, logs and health |
| [scheduling.md](scheduling.md) | Implemented subset | Scheduled-task lifecycle |
| [image_library.md](image_library.md) | Implemented subset | Flat image storage and browser library |
| [security_trust.md](security_trust.md) | Loopback baseline | Threat model and enforced boundaries |
| [deployment_operations.md](deployment_operations.md) | Local + registry baseline | Containers, Pi, image distribution, updates, sync and backup |
| [verification.md](verification.md) | Partial MVP | Test layers and release evidence |

Status is **implemented** only with code and an identified verification path, **partial** for a named subset, and **planned** only in design. The bootstrap repository must not be read as feature complete.

## Gaps

- Add source/test backlinks for each status after module paths stabilize.
- Promote statuses only with verification and close gaps in the same change.
