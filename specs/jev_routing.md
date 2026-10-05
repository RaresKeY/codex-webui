# Jev text-chat routing

Owners: `backend/app/task_router.py`, `routing_policy.json`, `/route` in `main.py`, `frontend/src/api.ts::sendPrompt`, and ChatSurface/Composer in `App.tsx`.

The policy is a source snapshot of `../jev-task-router/routing_policy.json` version `2026-10-05-v5` (source commit `1ee5700`). Luna executes established, documented, repeatable flows. Sol handles bespoke work, synthesis and foundation design; a new reusable workflow or initial visual baseline tends toward Sol high. Applying a known approach can still use Sol low. Model and deliberation are separate; no empirical capability or calibrated confidence claim is made.

`POST /api/threads/{id}/route` receives only `input`, blocks spending when Codex is offline, and makes one HTTPS call to `https://api.typesafe.ai/v1/systemone` with `model: jev-1.13.0`. State contains the original task and shared routing policy, without history, project files, identifiers or experimental labels. Two typed Choices ask for model and effort. Shared policy appears once in state; optional diagnostic questions are omitted and contextMissing remains null. Bounds cap the ask at 24 KB, serialized payload at 60 KB and reply at 128 KB. The request times out after 30 seconds and is not retried.

Validation requires the exact model, answer IDs/types, both allowed model choices, five effort choices, finite probability values summing within 0.025 of one, Choice matching a maximum, finite confidence, and nonnegative integer usage. Invalid/missing/inconsistent answers fail closed. Safe output includes chosen model/effort, separate confidence, null diagnostic field and policy version; raw replies and prompts are not persisted or logged.

The frontend awaits route → `thread/resume` model change → `turn/start` original ask with matching model/effort. Neither model change nor ask submission occurs after a routing error; ask submission does not occur after a model-change error. On a provisional unmaterialized thread, inherited resume fallback confirms the loaded thread and `turn/start` explicitly applies the same selected model. New chats explicitly use legacy Codex history. Existing incompatible paginated chats fail before ask submission with an instruction to start a new chat. No stored history or global Codex configuration is changed.

A synchronous submit guard and busy state prevent double clicks. Failed drafts stay editable; no hidden retry is made. Changing chats cancels a pending route and stops subsequent model/turn submission; an already dispatched turn remains Codex-owned. Native turn notifications remain authoritative after submission. Header shows the latest chosen model; assistant messages keep per-message model provenance.

Credentials are read directly from JEV_API/TYPESAFE_API_KEY environment or the configured external file, never sourced as shell code or copied into frontend/image layers. The container launcher mounts `../jev-pipelines/.env` read-only when present. Keys and provider error bodies are never returned to the browser.

Verification: `backend/tests/test_task_router.py` checks strict validation, input isolation, credential precedence, one transport call, safe errors and zero Codex calls from routing. `frontend/src/routed-send.test.ts` checks awaited three-request ordering, exact text/model/effort, failure barriers and navigation cancellation. Tests use fixtures and do not spend inference calls.

## Gaps

- No paid Jev/Codex end-to-end smoke has been run here.
- No project brief or conversation context is supplied; follow-up estimates can have missing context.
- Independent model and effort predictions are not a joint distribution or measured task success.
- Schedules and realtime voice retain inherited execution paths.
