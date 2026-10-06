# Jev run ordering and disclosure

Runs display in ascending stable activity ID order. Hydration retains descending API cursor semantics; older pages prepend above existing runs, and live new runs append below. Rows start closed, preserve manual disclosure state during live updates, and use the shared right/down chevron convention. Automatic selected-run expansion has been removed.

Production Firefox fixtures passed at 1440×1000, 390×844 and 320×640, checking chronological order, initial collapse, arrow transforms, older pagination, newest insertion, preserved manual opening, event-driven stages and chat isolation. Candidate passed 200 backend and 104 frontend tests plus offline native lifecycle checks.

## Gaps

- No paid inference was used; captures contain synthetic run metadata.
