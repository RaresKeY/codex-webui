# Desired system architecture

Keep the current modular monolith until measurements justify a split. FastAPI/Python owns HTTP, domain services, persistence, process supervision, schedules, and storage; React/TypeScript consumes typed normalization boundaries over HTTP and WebSockets. Modules are projects, conversations, runs, Codex adapter, workspaces/files, schedules, images, usage, updates, and security.

Streaming should reconnect with bounded replay by event ID. Persisted run state outlives requests. SQLite remains preferred for one device. Abstract only useful repository boundaries. C/native work follows profiling and requires both target architectures or a fallback.

The primary adapter now owns a host App Server over private stdio inside a loopback Mac companion. The optional container remains a secondary deployment with container tools. If a future split or remote runner is needed, it must remain a narrow authenticated protocol endpoint rather than a general shell or Docker socket.

## Gaps

- Decide API versioning, whether generated clients replace hand normalization, persisted event replay, and measured performance budgets.
- Define signed Mac lifecycle packaging, compatibility ranges, and whether worker separation is ever needed.
