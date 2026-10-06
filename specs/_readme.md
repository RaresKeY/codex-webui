# Specifications map

`specs/` is committed project memory for current ground truth. Describe only behavior supported by code and verification. Desired behavior belongs in `design/`.

| Document | Status | Ground-truth ownership |
| --- | --- | --- |
| [jev_routing.md](jev_routing.md) | Backend-enforced text-chat path | V5 Auto policy, per-chat manual selection, acknowledged model change and exact user ask |
| [jev_activity.md](jev_activity.md) | Implemented bounded metadata | Jev sidebar, attempts, detailed decisions, advisory information needs and actual turn status |
| [chat_management.md](chat_management.md) | Implemented | Native archive/restore/delete, confirmations and project deletion |
| [project_launch.md](project_launch.md) | Implemented | Project prompting, name-first creation, unassigned chats and actual last-model labels |
| [new_chat_launch.md](new_chat_launch.md) | Implemented | Default prompt launch page, overlapping threads and unread activity |
| [color_theme.md](color_theme.md) | Shared dark palette | Reusable color roles, neutral Markdown headers and shared sidebar surfaces |
| [chat_interactions.md](chat_interactions.md) | Implemented bounded chat subset | Startup, skill/plugin/app/file mentions, per-turn effort, images, one activity indicator and context totals |
| [chat_permissions.md](chat_permissions.md) | Per-chat native permission presets | Composer permissions, auto review, YOLO, new-chat inheritance, acknowledgement and persistence |
| [sidebar_navigation.md](sidebar_navigation.md) | ChatGPT-style navigation | Sidebar hierarchy, project filtering, search, keyboard/touch and drawer focus |
| [product_scope.md](product_scope.md) | WebUI 2 | User roles, milestone surface, projects and chats |
| [browser_integration.md](browser_integration.md) | Experimental Linux + container bridge | Audited Jev browser, dynamic tools, live sidebar and cursor |
| [architecture.md](architecture.md) | Python companion + container | Components, boundaries, flow and source ownership |
| [codex_app_server.md](codex_app_server.md) | Protocol subset + Jev ordering | Host Codex adapter, resumable sessions, approvals, and realtime |
| [persistence_model.md](persistence_model.md) | Organization + turn selections | Records, identifiers, per-turn model/effort, migrations and retention |
| [workspace_files.md](workspace_files.md) | Inherited subset | Workspace roots, browser and file safety |
| [context_panel_capabilities.md](context_panel_capabilities.md) | Implemented bounded subset | Context tools, backing boundaries, and Desktop/ChatGPT Project distinction |
| [usage_observability.md](usage_observability.md) | Partial MVP | Context/usage display, logs and health |
| [scheduling.md](scheduling.md) | Inherited subset | Scheduled-task lifecycle |
| [image_library.md](image_library.md) | Inherited subset | Flat image storage and browser library |
| [security_trust.md](security_trust.md) | Loopback container + private Tailscale access | Threat model and enforced boundaries |
| [deployment_operations.md](deployment_operations.md) | Rootless Podman + host Tailscale Serve | Local/private launch, containers, image distribution, updates, sync and backup |
| [verification.md](verification.md) | Partial MVP | Test layers and release evidence |

Status is **implemented** only with code and an identified verification path, **partial** for a named subset, and **planned** only in design. Inherited functionality does not imply fresh live verification; see verification.md.

## Gaps

- Add source/test backlinks for each status after module paths stabilize.
- Promote statuses only with verification and close gaps in the same change.
