# Product experience

The experience should feel familiar to a ChatGPT user while remaining visibly local and workspace-aware. It should reveal what Codex is doing, where it operates, and whether a conversation can truly resume.

The desktop shell uses a left project/conversation/search rail, central transcript/run timeline/composer, and collapsible right workspace tree/preview. Settings separates upstream facts from estimates: runtime version, auth readiness without secrets, model/config, context, usage, storage, and update state. Narrow screens turn sidebars into mutually exclusive drawers. Keyboard navigation, focus restoration, screen-reader labels, reduced motion, and contrast are first class.

Current search sends authoritative `searchTerm` queries to Codex, sorts by upstream recency, and adds local project filtering plus recent/oldest presentation. Desired expansion adds workspace, status, model, time, title, and usage dimensions. Badges should distinguish native-resumable, unavailable, running, interrupted, and archived sessions.

## Gaps

- User-test density and latency on Pi-class hardware and small laptops.
- Decide expanded search privacy, bulk organization, project nesting, Markdown/diff rendering, notifications, themes, and command palette.
