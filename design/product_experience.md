# Product experience

One quiet sidebar and a readable conversation form the primary workspace. Neutral charcoal surfaces, generous spacing, restrained icons and a compact rounded composer provide a familiar ChatGPT-style chat experience. Keep local workspace identity subtle and functional; preserve approvals, commands, native history and tool detail through progressive disclosure.

Keep conversation previews, project names and timestamps behind hover summaries and a small details disclosure. Show its control on hover, keyboard focus and touch layouts; expanding details must not navigate away from the current conversation.

Every text ask uses automatic Jev model/effort selection enforced by the backend. Show choosing, switching and sending state; show selected model provenance; keep the exact draft on errors and preserve whitespace when sending. Expose workspace tools from a collapsed context panel. Projects, scheduled tasks, images and settings belong in the single sidebar. On phones navigation and context are exclusive drawers.

## Experimental browser

The experimental Browser panel follows the reference split conversation/browser experience: visible address chrome, automatic opening on agent actions, smooth cursor movement, and the existing narrow-width drawer. See [../specs/browser_integration.md](../specs/browser_integration.md) for current bounds.

## Integrated pane presentation

The context sidebar should read as part of the app: a square, edge-attached split next to the conversation, with a compact aligned header and neutral tool selection. Its closed top-right control remains quiet and reachable; narrow screens attach the pane to the viewport edges.

## Gaps

- Decide user-controlled model overrides only if requested; the current requested flow is automatically routed.
- Add real microphone validation and optional project-brief routing only with a defined input/privacy contract.
