# Usage and observability

## Status

Implemented upstream usage/context subset and redacted local diagnostics.

## Source Sync

- Status/usage endpoints: `backend/app/main.py`.
- CLI version and process errors: `backend/app/codex_client.py`.
- UI mapping and formatting: `frontend/src/api.ts`, `frontend/src/App.tsx`, and `frontend/src/token-format.ts`.

## Behavior

`GET /api/usage` requests `account/rateLimits/read` and `account/usage/read` independently and reports each failure without inventing values. Streaming `thread/tokenUsage/updated` events update context percentage. `GET /api/system` reports Python/platform, the configured local/container runtime, configured Codex executable name, detected CLI version, initialization metadata/error, policy defaults, workspace root, and disk totals.

`GET /api/health` reports healthy/degraded App Server state and database initialization. No third-party telemetry is configured. Prompts, outputs, file contents, environment values, authentication material, and App Server stderr are not retained in application logs by default.

The Settings usage card abbreviates token totals using the existing thousands and millions rules and a billions unit for values at or above one billion. Both lifetime and peak-daily totals share the same formatter. The visual abbreviation is paired with the exact, grouped token count for hover disclosure and assistive technology; unavailable values remain labeled `Unavailable`.

The composer context ring beside the model control uses `tokenUsage.last.totalTokens`, not accumulated `total.totalTokens`. Hover/focus exposes used tokens, total `modelContextWindow` and remaining capacity. Unknown counts/limits are explicitly unavailable; changing model clears stale context. Current native thread reads do not restore these values, so a reopened chat waits for a token-usage notification. `frontend/src/context-usage.ts` owns validation and labels.

Settings prefers the `codex` bucket in `rateLimitsByLimitId`, falling back to the legacy snapshot. Native `usedPercent` is validated as a finite 0–100 value; missing or malformed values stay unavailable. Cards and bars show remaining capacity (`100 - usedPercent`) with explicit used percentages beneath. Window labels come from `windowDurationMins`, so a weekly primary window is labeled Weekly rather than assumed five-hour. Reset timestamps are finite Unix seconds, displayed in minutes, hours or days; secondary resets are independent.

## Verification

October 6 limit correction is verified by 72 frontend tests, 142 backend tests, native lifecycle and Firefox Settings captures at desktop/phone widths (`evidence/ui/usage-limits/`).

Frontend tests cover nested usage, missing-value handling, K/M/B formatting boundaries, and exact accessible token labels. Backend tests cover degraded bootstrap and protocol failure state. The live smoke prints only pass/fail milestones.

## Gaps

- Health does not execute a database read/write probe or separate storage readiness.
- Add structured correlation/redaction tests, retention policy, and realtime connection diagnostics without exposing SDP/audio.
