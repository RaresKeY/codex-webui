VERDICT: APPROVE

SCOPE
- Codex WebUI 2 sidebar, existing React/CSS, desktop 1440×1000, phones 390×844 and 320×640, landscape 854×480; offscreen Firefox with mouse, keyboard and emulated touch.
- Dense synthetic history: 45 chats, seven projects and long titles. Search, empty/error, selected, focus, details and drawer states inspected.

FINDINGS
- App.tsx::ChatSidebar: filter chips and a count/sort strip competed with navigation. Replaced them with expandable project rows and quiet Your chats headings.
- styles.css sidebar rules: a permanently boxed search field and version badge made the header busy. Search is an icon/text row opening a focused field; the header retains Codex branding without the badge.
- Sidebar project section: only two filters exposed projects. New project opens the existing form, three projects appear initially, See more reveals all, and project selection/reset retains filtering.
- Narrow sidebar: background focus could escape the drawer. Background content is inert, Tab stays inside, Escape closes search/drawer, and focus returns to the opener.
- Dense lists: kept single-line title truncation, independent details, a single scroll area and a fixed profile row so the last chat and settings remain reachable.

CHANGES
- Updated sidebar hierarchy, icon/text alignment, row spacing, surfaces, responsive width, safe-area padding and profile styling within the existing stylesheet.
- Added Ctrl+K/Cmd+K search access and bounded remote-search failure feedback; existing cancellation and stale-result guards remain intact.
- Retained chat creation/selection, project creation/filtering/management, Images, Tasks, settings, sorting, details, draft state, backend routing and composer controls.
- Updated specs/sidebar_navigation.md, product scope and design notes; adapted existing browser selectors to the new sidebar.

VERIFICATION
- python3 tools/check_sidebar_browser.py --baseline-bundle /tmp/codex-webui2-sidebar-baseline
- python3 tools/check_sidebar_browser.py
- tools/build-image.sh: frontend build/typecheck/lint/unit tests, backend tests and native offline lifecycle.
- Matched before/after desktop, phone, narrow-phone and landscape screenshots are in this directory. checks.json records project expand/filter/reset, chat order/details, search focus/remote/empty/error, secondary navigation, New project form, drawer focus trap/Escape, inert background, touch selection, dense-list scrolling, history failure/retry and empty-workspace New chat.
- Final build passed 70 frontend tests and 139 backend tests plus the native offline lifecycle. The deployed private HTTPS page passed desktop/phone shell, sidebar/drawer, profile and secure WSS checks with zero JavaScript errors. A separate Pi validated HTTPS health 200.
- Targeted browser checks passed with zero uncaught JavaScript errors and no inference; synthetic New chat invoked only the fixture creation API.

UNVERIFIED
- Physical iOS Safari and pixel-for-pixel parity with an unspecified ChatGPT app build. No sidebar reference screenshot was supplied; the implementation follows familiar app hierarchy and preserves available Codex destinations.
- Paid routing/inference and microphone capture; this sidebar change does not require either.
- The broader browser fixture's separately recorded typing-order issue remains outside this change; its sidebar selectors were updated, and the focused sidebar checker passed.
