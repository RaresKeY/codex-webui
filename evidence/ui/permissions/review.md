# Per-chat permission controls

The composer now exposes Default, Full access · Auto approve, and Full access · YOLO. Changes take effect after native acknowledgement and persist per chat. Auto approve uses Codex automatic review and can reject requests; YOLO skips approval prompts. Both stay within the existing runtime and mounts.

`tools/check_permissions_browser.py` tested the production bundle with synthetic fixtures in offscreen Firefox at 1440×1000, 390×844 and 320×640. `checks.json` records acknowledgement gating, keyboard/touch operation, draft retention, persistence, failed-change recovery and active-turn disabling. The paired desktop/phone images show the previous composer and new control; menu screenshots cover desktop and narrow phones.

The build passed 132 backend and 68 frontend tests. Disposable native Codex checks observed the effective settings for each preset without inference. No live chat permissions were changed for verification. The final runtime was deployed at the private Tailscale URL; production HTTPS Firefox confirmed the control and healthy WSS on desktop and phone. Local and separate Pi certificate-validated health checks returned 200.

## Gaps

Paid model execution and automatic-review decisions were not exercised. The broader existing browser typing fixture has a separately recorded input-order failure; these focused checks do not claim to fix it.
