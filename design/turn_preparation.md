# Jev search and project context preparation

Requested on 2026-10-06. Search, freshness, and project-context diagnostics are implemented; automatic preparation and maintained summaries remain TODO and research. Before executing a turn, Jev should assess whether online information and project context would improve the requested result, alongside model and reasoning effort. The diagnostics apply to all Auto classifications, including Luna low; manual selection continues to skip Jev. A simple task can still need current facts or project context.

Current routing asks five typed questions for model, effort, and the three information-needs diagnostics, receiving the unchanged ask plus routing policy. It does not receive a project summary or prepare search/context; see [jev_routing.md](../specs/jev_routing.md).

## Questions and proposed preparation

| Question | Decision to investigate |
| --- | --- |
| Would this turn benefit from online search? | Search for missing external facts, documentation, or sources when they affect the current deliverable. |
| Does this turn specifically need up-to-date information? | Identify changing prices, tool availability, library versions, APIs, compatibility, or recent changes. Distinguish a live lookup from retrieval of established information. |
| Would this turn benefit from project context? | Use a relevant maintained summary and focused specs for existing behavior, constraints, decisions, and follow-up references. Project selection alone does not make context necessary. |
| Is the available project summary current and sufficient? | Reuse it when relevant and current; refresh or read authoritative project files when stale, absent, or incomplete. |

Search and project context can both be useful. Stable project decisions should come from maintained project files; changing external claims should be verified against appropriate current sources. Recording a future investigation only requires recording it, not performing that investigation.

## Project summaries

Investigate a concise summary file derived from the project's specs and relevant source, with source references and freshness metadata. Keep it synchronized when behavior or durable decisions change. A summary should route readers to authoritative files and preserve uncertainty; it must not silently replace current source or specs. Resolve summaries only within the configured workspace and existing file-access boundaries.

## TODO

- [x] Define typed Jev answers for search benefit, freshness need, and project-context benefit, with strict validation and decision provenance.
- [ ] Define missing/stale-summary detection once a project brief is available.
- [x] Apply advisory diagnostics to every automatic classification, including Luna low.
- [ ] Decide preparation behavior and whether manual selections should have a separate diagnostic path.
- [ ] Define summary discovery, bounded relevant reads, creation/refresh ownership, and synchronization with project changes.
- [ ] Connect validated decisions to actual search/context preparation through supported App Server interfaces, keeping the exact user ask and model-change acknowledgement barriers.
- [ ] Define visible behavior for preparation failures and unavailable sources without hidden retries or unsupported freshness claims.
- [ ] Verify the integrated flow with synthetic fixtures before any explicitly requested paid classification study.

## Research

- Compare task-only classification with classification supplied a concise current project brief. Determine when the context-needed decision itself requires a brief and how to avoid irrelevant project complexity inflating a greeting or routine ask.
- Compare Luna low with preparation against execution without preparation, and examine whether the same questions help other selections. Measure answer correctness, source freshness, context relevance, latency, and usage separately from classifier confidence.
- Establish summary freshness checks using source revisions or content hashes, including dirty files, changes made outside WebUI, and concurrent updates. Decide which changes require refresh and which can use focused reads.
- Verify search configuration against the installed App Server schema. Official Codex configuration distinguishes cached indexed results from live fetches; cached results alone do not establish current prices or versions. [OpenAI Docs config basics](https://learn.chatgpt.com/docs/config-file/config-basic#web-search-mode).
- Cover greetings with/without a selected project, current prices/tool/library questions, fixed-version documentation, project-specific follow-ups, stale/missing summaries, and requests that need both project context and external verification.

## Gaps

- Advisory questions are implemented for Auto; preparation execution and manual-selection behavior remain undecided.
- Summary location, freshness contract, synchronization trigger, and size budget remain undecided.
- Search/context preparation is not implemented; classification quality and downstream benefit remain unmeasured.
