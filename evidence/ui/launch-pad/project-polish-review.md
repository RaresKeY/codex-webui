VERDICT: APPROVE

SCOPE
Project-scoped quick launch, creation dialogs, unassigned New chat and bottom last-turn model labels. Inspected App.tsx, LaunchPad.tsx, Composer.tsx, API adapters, model metadata queries and routing policy. Firefox checks cover desktop 1440×1000, phones 390×844/320×640 and landscape 854×480.

FINDINGS
Patched first-project fallback, missing project prompting, missing creation errors/double-submit guard, keyboard dialog containment, and model labels inferred from thread defaults. No actionable finding remains in this reviewed scope.

CHANGES
Shared persistent quick composer across project/new-chat navigation; project-scoped recents and pending jobs; name-first creation with optional folder, description and colors; native null-project assignment; recorded last-turn model/effort near bottom controls; explicit Luna/low greeting anchors without weakening the Sol teaching preference.

VERIFICATION
Container build wrapper: frontend lint/type/build and 87 tests; 151 backend tests and native offline lifecycle. Synthetic Firefox launch/project, sidebar and existing-chat checkers passed: exact prompts, independent submissions, native selection labels, creation success/failure and duplicate guards, touch layouts, dialog Tab/Escape and narrow expanded forms. Existing launch evidence provides the prior surface; new desktop-project, desktop-project-create, narrow-project-create and narrow-composer-last-model images show the final surface. Deployed amd64 runtime is healthy; its loopback/private HTTPS bundle matches the tested frontend.

UNVERIFIED
No paid Jev classification or native model execution, live microphone, or ARM64 runtime verification. Workspace-invariant asks and greeting policy payloads are tested; actual live greeting choices are not claimed.
