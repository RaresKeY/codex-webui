# Direct browser input review

VERDICT: APPROVE

## Scope and changes

Production frontend in offscreen Firefox at 1440×1000, 390×844 and 320×640. Synthetic APIs and a placeholder JPEG test chrome, scaled mouse coordinates, typing, Control/View only and phone bounds. Separate real audited Chromium smoke exercises actual pages, manual field input/backspace, a checkbox inside an iframe, agent observation invalidation and persistent-cookie survival across a clean browser restart. No external-site interaction, CAPTCHA solving or model inference is part of these tests.

Human input uses a separate bounded same-origin API/Unix bridge, not the agent dynamic-tool schema. Queueing preserves input order, coalesces text, limits backlog, and discards pending input on pane exit. Mouse clicks map the scaled screenshot to 1280×900; the wheel scrolls the remote page. Keyboard/paste and a phone text row operate on the remote focused field. Escape releases local focus. The dedicated existing profile retains persistent site cookies and storage, without cookie export or host-profile import.

## Verification

- `./tools/validate.sh`: backend tests, frontend type/build/lint and 109 frontend tests.
- `tools/build-image.sh`: final runtime passes 203 backend tests and native offline Codex lifecycle without inference.
- `backend/tests/test_browser.py`: human route origin/schema/bounds, thread isolation, agent schema separation, stale observation rejection and bridge transport.
- `tools/smoke_browser.py --run`: audited real Chromium, iframe checkbox click, native typing/backspace and persistent cookie surviving clean shutdown/reopening in an isolated temporary profile.
- `tools/check_jev_browser.py`: production UI, scaled click and keyboard packets, mode toggle, desktop/phone input affordances and retained Jev behavior, zero uncaught errors.
- Private HTTPS deployment verified healthy, exact built assets, browser agent availability, accepted same-origin WebSocket and rejected foreign origin. Host bridge restarted and the user browser view reopened with the retained profile.

## Gaps

Session cookie expiry remains site-controlled; there is no forced persistence or expiry extension. Physical touch/IME, drag/multi-touch, remote clipboard copy and real Google CAPTCHA/login reliability are unverified or unsupported. Target arm64 hardware remains unverified; no container/native architecture or dependency changes were introduced.
