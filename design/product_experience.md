# Product experience

The experience should feel familiar to a ChatGPT user while remaining visibly local and workspace-aware. It should reveal what Codex is doing, where it operates, and whether a conversation can truly resume.

The desktop shell uses a stable left application rail plus project/conversation/search navigation, a flexible central transcript/run timeline/composer, and an inset collapsible context panel on the right. That panel is a general tool surface rather than an Explorer identity: Outputs, read-only Terminal activity, Side chats, Explorer, and bounded Changes work today, while Browser and future tools share the same scalable selector model. Planned tools are labeled honestly until they have a real public-protocol or safe companion implementation. Active turns have a prominent list marker, header pill, and in-transcript state; item cards retain smaller tool-specific progress. Assistant and readable reasoning text use a restrained prose system for headings, lists, quotes, tables, safe links, inline code, and copyable fenced code; partial Markdown is reparsed as streaming source grows. Literal operational output is visually and semantically separate. The composer includes an explicit microphone control only when realtime capability is verified, with disabled reason, connecting/live/error state, and guaranteed track teardown. Settings separates upstream facts from estimates: runtime version, auth readiness without secrets, model/config, context, usage, storage, and update state. Narrow screens turn navigation and context into mutually exclusive drawers. Keyboard navigation, focus restoration, screen-reader labels, reduced motion, and contrast are first class.

Current search sends authoritative `searchTerm` queries to Codex, sorts by upstream recency, and adds local project filtering plus recent/oldest presentation. Desired expansion adds workspace, status, model, time, title, and usage dimensions. Badges should distinguish native-resumable, unavailable, running, interrupted, and archived sessions.

New conversations use a fast local provisional title after the first turn is accepted: the first meaningful prompt line is cleaned and bounded for the sidebar, without a second model request or hidden transcript mutation. The header exposes inline manual rename for meaning the heuristic cannot infer. Existing or manually assigned names are never replaced automatically, and the App Server remains canonical through its name update notification.

## Gaps

- User-test density and latency on Pi-class hardware and small laptops.
- Decide voice selection/transcript grouping, expanded search privacy, bulk organization, project nesting, syntax highlighting/diff rendering, notifications, themes, and command palette.
