# Sources and outputs overlay

Opening the summary does not alter transcript, Worked disclosure or composer geometry. Entering the narrow viewport at 1000px or less closes it automatically, with explicit reopening supported on phones. This uses the existing overlay surface and header toggle.

Production Firefox fixtures compare exact row/composer x positions and widths before and after opening. Desktop 1440×1000 and phone 390×844/320×640 checks pass, including automatic close and bounded manual reopening. Candidate passed 200 backend and 104 frontend tests plus offline native lifecycle checks.

## Gaps

- Captures use synthetic history without paid inference.
