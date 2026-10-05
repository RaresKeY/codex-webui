# Specifications map

`specs/` is committed project memory for current ground truth. Describe only behavior supported by code and verification. Desired behavior belongs in `design/`.

| Document | Status | Ground-truth ownership |
| --- | --- | --- |
| [jev_routing.md](jev_routing.md) | Backend-enforced text-chat path | V5 policy, typed decisions, acknowledged model change and exact user ask |
| [chat_interactions.md](chat_interactions.md) | Implemented bounded chat subset | Progressive startup, plugin mentions, image previews, one activity indicator and context totals |
| [product_scope.md](product_scope.md) | WebUI 2 | User roles, milestone surface, projects and chats |
| [architecture.md](architecture.md) | Python companion + container | Components, boundaries, flow and source ownership |
| [codex_app_server.md](codex_app_server.md) | Protocol subset + Jev ordering | Host Codex adapter, resumable sessions, approvals, and realtime |
| [persistence_model.md](persistence_model.md) | Inherited subset | Records, identifiers, migrations and retention |
| [workspace_files.md](workspace_files.md) | Inherited subset | Workspace roots, browser and file safety |
| [context_panel_capabilities.md](context_panel_capabilities.md) | Implemented bounded subset | Context tools, backing boundaries, and Desktop/ChatGPT Project distinction |
| [usage_observability.md](usage_observability.md) | Partial MVP | Context/usage display, logs and health |
| [scheduling.md](scheduling.md) | Inherited subset | Scheduled-task lifecycle |
| [image_library.md](image_library.md) | Inherited subset | Flat image storage and browser library |
| [security_trust.md](security_trust.md) | Loopback container baseline | Threat model and enforced boundaries |
| [deployment_operations.md](deployment_operations.md) | Rootless local Podman | Local launch, containers, image distribution, updates, sync and backup |
| [verification.md](verification.md) | Partial MVP | Test layers and release evidence |

Status is **implemented** only with code and an identified verification path, **partial** for a named subset, and **planned** only in design. Inherited functionality does not imply fresh live verification; see verification.md.

## Gaps

- Add source/test backlinks for each status after module paths stabilize.
- Promote statuses only with verification and close gaps in the same change.
