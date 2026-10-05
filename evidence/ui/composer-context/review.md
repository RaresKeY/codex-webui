# Composer context indicator

VERDICT: PASS for checked scope.

SCOPE: Move context from the header to the composer near model controls, matching the supplied small ring and three-line tooltip reference.

CHANGES: Compact ring immediately before the model selector. Tooltip reports context-window percentage used/left and compact token counts; accessible label retains exact totals. Hover, focus and tap open it; Escape/blur close it. Body portal plus clamped viewport placement prevents clipping at narrow widths. Native last-context accounting and unknown-state behavior are preserved.

VERIFICATION: Production Firefox verifies no header duplicate, 13% used/87% left from synthetic latest context, exact accessible counts, desktop and phone tooltip placement and 320px no-overflow. Matched before/after sidebar captures and tooltip screenshots are synthetic. 75 frontend tests, type checking, lint, production image build, 143 backend tests and offline native lifecycle passed. No paid inference.

UNVERIFIED: Physical phone Safari. Native reopened histories still await usage notifications, as before.

Deployment: image `658b7c27a97c`, container `586201f37561`; zero active turns before restart. Loopback and private HTTPS returned healthy native connectivity and the new bundle.
