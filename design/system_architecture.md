# Desired system architecture

Keep the current modular monolith until measurements justify a split. FastAPI/Python owns HTTP, domain services, persistence, process supervision, schedules, and storage; React/TypeScript consumes typed normalization boundaries over HTTP and WebSockets. Modules are projects, conversations, runs, Codex adapter, workspaces/files, schedules, images, usage, updates, and security.

Streaming should reconnect with bounded replay by event ID. Persisted run state outlives requests. SQLite remains preferred for one device. Abstract only useful repository boundaries. C/native work follows profiling and requires both target architectures or a fallback.

The MVP adapter owns an in-container App Server. The target architecture also permits an authenticated external runner so the UI container can drive Codex in the host's actual tool environment without broad host mounts. That runner is a narrow protocol endpoint, not a general shell or Docker socket.

## Gaps

- Decide API versioning, whether generated clients replace hand normalization, persisted event replay, and measured performance budgets.
- Define the external runner lifecycle, compatibility, and whether worker separation is ever needed.
