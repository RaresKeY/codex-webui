# Chat permissions

## Ownership

`backend/app/permissions.py` defines bounded presets. `chat_service.py` serializes native permission changes with text submissions, requires acknowledgement and reapplies the saved choice before every WebUI text turn. `main.py` exposes only a typed GET/PATCH permissions surface. `frontend/src/PermissionsButton.tsx` projects the composer menu through `api.ts`.

## Behavior

The composer has a keyboard/touch-accessible Permissions button with three choices. Default uses the deployment's configured sandbox and approval policy with the user as reviewer. Full access · Auto approve uses `dangerFullAccess`, `on-request` and `auto_review`; eligible requests are reviewed automatically and may still be denied. Full access · YOLO uses `dangerFullAccess`, `never` and the user reviewer (inactive for non-interactive approval policy). Full access is within the existing runtime and mounts; it does not grant host administrator rights, replace container isolation or override managed requirements. The menu describes files/network access and approval behavior, displays the last acknowledged choice, and distinguishes YOLO with its text and icon as well as color. It adds no confirmation step.

`GET /api/threads/{id}/permissions` reads the saved WebUI selection, defaulting to Default; it does not claim to introspect external CLI sessions. `PATCH` accepts only `{mode: "default" | "full-auto" | "yolo"}`. It acquires the same per-thread lease as text submission, rejects an active native turn, loads the native thread, and awaits `thread/settings/update` with `approvalPolicy`, `approvalsReviewer` and `sandboxPolicy`. Only an empty-object native acknowledgement permits saving `chat-permissions:<thread-id>` in the existing SQLite settings table and returning `acknowledged: true`. No prompt, transcript or credential is stored. A rejected or unacknowledged update retains the prior saved selection; a post-acknowledgement database failure explicitly reports that the native change occurred but was not saved. No mutation automatically retries.

The UI loads a per-chat selection, retains the old label on failure, shows explicit error/Refresh feedback, and prevents sending or starting voice while a permission change is pending. Changes are disabled while a turn, submission, hydration or voice session is active. The menu closes on selection acknowledgement, outside click or Escape, restores trigger focus after explicit close, and supports Arrow/Home/End navigation. Its size is bounded by the composer and viewport, including narrow screens.

Every interactive text submission reads its saved preset before paid routing, preserving Auto Jev selection or the saved manual model/effort → acknowledged model/effort/permission binding → exact original ask. Both `thread/settings/update` and subsequent `turn/start` carry the same permission tuple. Legacy explicit REST approval/sandbox overrides remain accepted and are included in both calls. Persisted selections are per chat, survive app/database restart, and do not change other existing chats, schedules or Codex's global config. The latest acknowledged explicit permission selection is saved atomically with the chat selection as `new-chat-permissions`. New chats snapshot that preference and send its sandbox, approval policy and reviewer in native `thread/start`, then save the snapshot after the successful creation response; this does not overwrite the latest preference during concurrent creation. Existing chats without a saved selection remain Default. Invalid saved presets fail closed before routing.

## Verification

Backend tests cover all presets, exact native payloads and asks, thread separation, rejection/invalid acknowledgements, active turns, concurrent mutation/submission, acknowledgement ordering and SQLite reopening. Frontend API tests cover one explicit change, matching acknowledgement, invalid state and rejection without retry. `tools/check_thread_lifecycle.py` validates the real packaged Codex settings acknowledgement and effective `thread/settings/updated` policies in an offline container with disposable state, without inference. Browser checks cover the production menu and sending state with synthetic API data.

## Gaps

- Saved WebUI presets are not an introspection or synchronization mechanism for permission changes made by other native clients.
- The existing approval UI handles command/file decisions; other native elicitations and automatic-review status presentation remain outside this feature.
- Full paid execution, automatic-review decisions and managed-policy rejection require separately authorized live evidence; no paid calls are required for settings verification.
- Per-turn permission provenance, fork copying and preference pruning are not implemented.
