# Sidebar and live selection follow-up

Removed the left-navigation Jev shortcut. Jev remains a right sidebar tab with a distinct workflow icon. Default pane width is 440px desktop and 400px at the 1280px breakpoint, retaining drag overrides and bounded phone layout. The composer now uses the header's live model/effort projection instead of prioritizing the previous reply's selection. Native result decisions remain an acknowledgement fallback.

The address bar accepts plain domains as text and normalizes them to HTTPS before navigation. Explicit HTTP(S), paths, ports, fragments and queries are preserved, with backend validation authoritative. Frontend tests include URLs embedded in query values, invalid/credential-bearing input and protocol handling. The production browser fixture submits duckduckgo.com through the real form and asserts https://duckduckgo.com/ in the submitted action and resulting address.

Desktop, 390px and 320px Jev pane checks pass, including removal of the left shortcut, resizing, event-driven run state, chat isolation and normalized browser submission. Core desktop/phone checks assert the composer model/effort matches the header during a live synthetic turn. Candidate passed 200 backend and 107 frontend tests, type/lint/build and offline native lifecycle checks.

## Gaps

- Navigation fixtures exercise the UI/adapter boundary without requesting the external DuckDuckGo website.
- No paid inference or full accessibility audit was run.
