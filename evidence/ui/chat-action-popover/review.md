# Chat action popover

The chat ellipsis now opens a compact native top-layer popover with aligned icons, pin/lifecycle separation and a danger-colored Delete action. Metadata stays in the row tooltip and accessible description. It overlays scrollable history, clamps within the viewport, closes on outside pointer/Escape, restores trigger focus on Escape and permits only one open chat menu. Pending/error states and running-turn restrictions remain; pinning shares the synchronous mutation guard.

Production Firefox chat-management and dense sidebar regressions passed. Desktop 1440×1000 and phone 390×844/320×640 captures/checks cover unchanged history geometry, native top-layer visibility, viewport fit, Escape focus, pin, archive/restore/delete confirmations, failure and duplicate prevention. Candidate passed 200 backend and 104 frontend tests with type/lint/build and offline native lifecycle checks.

## Gaps

- Validation used workstation Firefox; no full cross-browser accessibility audit was run.
- Fixtures use synthetic chats and do not mutate live history.
