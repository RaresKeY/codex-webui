# Work activity disclosures

## Ownership and boundaries

`frontend/src/WorkActivity.tsx` owns ActivityDisclosure, ActivitySurface, CommandCard, CommandGroup, FileChangeActivity, ReasoningActivity and SearchActivity. `work-activity.css` owns row geometry, disclosure arrows, indentation and native output scrolling. App composes these components with adapter-normalized StreamEvent data; it does not duplicate Shell or summary markup. No dependency, event schema or backend behavior changes are required.

## Turn grouping

Native turn IDs group public commentary (`phase: commentary`), reasoning summaries, commands, file changes and web searches into a closed-by-default Worked disclosure. Consecutive commands have a compact Ran/Running N commands disclosure; the group remains mounted as live commands arrive to preserve disclosure state. Inside a group, each command is a one-line, ellipsized Ran/Running row with its own disclosure. Opening it reveals a Shell surface with full native command/output, bounded scrolling, elapsed duration when known and an honest exit/outcome label. Failed commands remain visibly marked even while collapsed. Native command and output fields are kept separately; legacy combined events retain a fallback projection. File changes also use compact closed-by-default rows, revealing the bounded native diff inside a Changes surface. Pending approvals and critical status messages stay visible. Native final answers and unknown-phase legacy assistant messages remain visible outside it, as do pending approvals. Jev process details are available only in the sidebar tab. Working/Worked labels use the active native turn and native `durationMs`; missing duration yields Worked without an invented number. Raw reasoning is still excluded. Grouping stops at visible events, preserving approval and response chronology. Search rows use a shared compact baseline and ellipsized query. Expanding reveals the public work in its original order; the final answer remains outside the disclosure.

## Shared presentation

Native details/summary semantics provide mouse and keyboard expansion. Rows start closed; stable event/group keys and local disclosure state preserve manual expansion during updates. Desktop rows are 30px tall, coarse-pointer rows at least 44px. Icons share one baseline; ellipsized labels shrink to fit, and the right/down arrow immediately follows the label rather than sitting at the panel edge. Failure status stays visible after the arrow. Singular groups say “Ran 1 command”.

Expanded command groups and reasoning add a 19px child indent with a subtle tree divider. Shell/Changes surfaces indent beneath their parent row and retain the existing palette. Output is exact preformatted native text, bounded vertically (320px desktop, 260px narrow). Horizontal/vertical scrolling uses a native pre surface with 16px bottom padding so an overlay scrollbar cannot cover the final text line. Do not reintroduce legacy command CSS overrides in styles.css.

## Verification

`tools/check_turn_browser.py` checks production Firefox at 1440×1000, 390×844 and 320×640: nested disclosure, keyboard opening, bounded output, failures, tree offsets, label-adjacent arrows and scrollbar clearance. Existing adapter/grouping tests protect native projection and chronology. No inference is needed for these fixtures.

## Gaps

- Native scrollbar behavior varies by operating system; current visual checks run on workstation Firefox.
- Browser fixtures are not a full accessibility audit.
