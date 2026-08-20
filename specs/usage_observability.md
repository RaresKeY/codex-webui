# Usage and observability

## Status

Implemented upstream usage/context subset and redacted local diagnostics.

## Source Sync

- Status/usage endpoints: `backend/app/main.py`.
- CLI version and process errors: `backend/app/codex_client.py`.
- UI mapping and formatting: `frontend/src/api.ts`, `frontend/src/App.tsx`, and `frontend/src/token-format.ts`.

## Behavior

`GET /api/usage` requests `account/rateLimits/read` and `account/usage/read` independently and reports each failure without inventing values. Streaming `thread/tokenUsage/updated` events update context percentage. `GET /api/system` reports Python/platform, `localhost-companion` runtime, configured Codex executable name, detected CLI version, initialization metadata/error, policy defaults, workspace root, and disk totals.

`GET /api/health` reports healthy/degraded App Server state and database initialization. No third-party telemetry is configured. Prompts, outputs, file contents, environment values, authentication material, and App Server stderr are not retained in application logs by default.

The Settings usage card abbreviates token totals using the existing thousands and millions rules and a billions unit for values at or above one billion. Both lifetime and peak-daily totals share the same formatter. The visual abbreviation is paired with the exact, grouped token count for hover disclosure and assistive technology; unavailable values remain labeled `Unavailable`.

## Verification

Frontend tests cover nested usage, missing-value handling, K/M/B formatting boundaries, and exact accessible token labels. Backend tests cover degraded bootstrap and protocol failure state. The live smoke prints only pass/fail milestones.

## Gaps

- Health does not execute a database read/write probe or separate storage readiness.
- Add structured correlation/redaction tests, retention policy, and realtime connection diagnostics without exposing SDP/audio.
