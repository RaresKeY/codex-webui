# Sessions and Codex integration design

Resume always uses Codex's durable thread/session identity. Local events reconstruct display state but never substitute for native continuation. Imported sessions retain upstream identity and can be organized without rewriting history.

The adapter should discover capabilities and keep a tested compatibility table. Run presentation preserves event order, approval/input states, cancellation, interruption, reconnect, and upstream usage provenance. Turn-level activity comes from turn notifications and remains visually distinct from command/item progress; a stable waiting response becomes one incrementally growing message rather than a sequence of replacements. Current approval cards show action/scope, disable while sending, resolve only after backend acceptance, and remain pending with a retry path on failure; future input types should preserve the same lifecycle invariant.

New App Server threads remain provisional until their first user message. Product flows must treat metadata-only hydration and first-turn materialization as a named state instead of presenting a resumed session or a history failure.

## Host App Server

The implemented Mac mode runs App Server as the selected host user inside a loopback companion and owns it over private stdio. Browser clients receive only task-specific HTTP/WebSocket projections; there is no generic command or raw App Server network endpoint. This reuses host login and tools without a container-to-host bridge or token.

The UI identifies the runtime as a localhost companion and distinguishes it from optional container execution. A future remote or container-to-host bridge would still require authenticated transport, version negotiation, workspace allowlists, revocation, message/concurrency caps, and a threat model.

## Gaps

- Expand the stable 0.147 thread/approval/realtime evidence across future supported upgrades.
- Decide whether a signed app wrapper or background launch agent owns the companion lifecycle.
- Choose transport, token lifecycle, and compromise recovery only if a remote/container bridge returns to scope.
- Decide event replay limits and recovery across incompatible Codex updates.
