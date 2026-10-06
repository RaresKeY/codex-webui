# Shared work activity presentation

WorkActivity.tsx supplies a reusable ActivityDisclosure and output surface for turn, command, file and reasoning presentation, plus a shared search row. work-activity.css replaces legacy overrides in styles.css. Rows are compact and aligned, arrows follow their labels, nested children indent 19px with a subtle divider, and preformatted output retains 16px clearance below the final text line. Single command groups use singular wording.

Production Firefox checks passed at desktop 1440×1000 and phone 390×844/320×640. Assertions check child offset, row height, arrow gap after animation settles, scroll-bottom clearance, output bounds, keyboard opening, failure states and unchanged chat/summary alignment. Core chat checks pass at desktop and phone. Frontend check passed type/build/lint and 104 tests. Runtime candidate passed 200 backend tests and the offline native lifecycle checks.

## Gaps

- Native scrollbar appearance varies across platforms; verification used workstation Firefox.
- Fixtures contain synthetic commands and no inference.
