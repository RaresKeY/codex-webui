# Usage limit correction

Settings previously displayed native usedPercent as an unlabeled percentage and full bar. Read-only native verification showed the primary Codex window was weekly and exhausted (100% used), rather than a five-hour window with 100% available. No inference was executed.

The display now shows remaining percentages and bars, explicit used percentages, actual window duration labels and independent reset times. Normalization prefers the native codex bucket, validates finite 0–100 usage, and keeps missing values unavailable. Tests cover alternate legacy buckets, weekly primary windows, snake-case compatibility, zero usage and malformed values.

Desktop and phone Settings evidence uses synthetic data only. Existing sidebar/chat navigation and drawer behavior are exercised by the same production Firefox checks. Local App Server protocol source and TUI confirm multi-bucket usage and remaining-capacity semantics.

## Gaps

Physical phone browsers remain unverified. Quota resets and credit consumption are not implemented; this change only reads and displays usage.

Verification passed: 72 frontend tests, build/type checking/lint, 142 backend tests, native offline lifecycle and production Firefox desktop/mobile checks. Deployed image `17dc49b89900`; loopback and private HTTPS serve the new bundle with healthy native connectivity. Zero active turns before replacement.
