# Usage and observability

`GET /api/usage` requests `account/rateLimits/read` and `account/usage/read` independently and reports each failure. `frontend/src/api.ts` maps nested primary/secondary rate limits plus lifetime tokens, peak daily tokens, current streak, and reset time; missing values remain `null`/Unavailable. Streaming `thread/tokenUsage/updated` events merge authoritative context-window percentage into the active conversation. `GET /api/system` reports Python/platform, configured Codex command, initialization info/error, approval/sandbox settings, workspace path, and disk totals.

`GET /api/health` reports overall/degraded, Codex availability/error, and a database `ok` label. The container health check calls it, so degraded Codex still counts as an HTTP-successful container. No third-party telemetry is configured.

## Gaps

- Map remaining runtime/storage settings fields and distinguish exact upstream usage provenance in detail views.
- Health does not execute a database probe or separate storage readiness; structured redaction/correlation and retention need implementation.
