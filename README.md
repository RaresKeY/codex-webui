# Codex WebUI 2

A local Codex chat app with a quieter ChatGPT-style interface, succeeding WebUI 1 in [RaresKeY/codex-webui](https://github.com/RaresKeY/codex-webui). It supports chat archive/restore and confirmed permanent deletion, plus project deletion that preserves chats and files. It retains native thread history, approvals, workspace tools, projects, schedules, images, and the experimental voice adapter. WebUI 1's tracked source and complete Git history are archived externally; its local checkout remains available as an archival reference.

A narrow utility rail and compact chat sidebar, readable conversations, user message bubbles, a compact composer, and optional workspace tools keep chat central. Command output and public thought summaries expand on demand. Desktop navigation collapses; phone navigation and context use exclusive drawers. The shell opens while history loads, `@` offers installed plugins, images preview inline with click-to-zoom and appear in the gallery from up to 100 loaded recent chats, and one activity indicator covers the message lifecycle. Hover the context ring for exact used/total/remaining token counts; unknown limits stay unavailable.

The browser submits each text message once to the backend. After checking that the conversation is available, the backend enforces this order:

1. Send the original ask to Jev (`jev-1.13.0`) using the task router's V5 policy.
2. Validate and select `gpt-6.1-sol` or `gpt-6-luna` and low/medium/high/xhigh/max effort.
3. Apply the selected model and effort with `thread/settings/update` and await its acknowledgement, loading the thread first if needed.
4. Send the unchanged ask through `turn/start` with that model and effort.

Jev failure, an invalid decision, or a rejected model change stops submission. There is no silent fallback or automatic retry. Failed drafts remain in the composer. Jev receives only the current ask; it receives no history, source files, account metadata, or credentials from Codex. Its confidence estimates are uncalibrated.

`POST /api/threads/{id}/messages` owns this complete operation; `/turns` is a routed compatibility alias. Caller-selected model/effort fields, thread creation with `prompt`, and direct steering cannot bypass routing. Leading/trailing whitespace is preserved through the composer, Jev payload and Codex input.

## Container launch

The built image is `localhost/codex-webui-2:local`:

```sh
./tools/run-container.sh --detach
```

Open **http://127.0.0.1:8766**. The launcher runs rootless Podman, publishes loopback only, mounts the workspace at its identical absolute path, mounts existing Codex state externally, and uses the separate `codex-webui-2-data` volume. It does not open a browser window.

For private Tailscale access, launch with `tools/run-container.sh --detach --tailscale`, then configure the host proxy with `tailscale serve --bg --yes --https=443 http://127.0.0.1:8766` (use `sudo` if Tailscale requires administrator access). The app allows the connected workstation's canonical `.ts.net` hostname and HTTPS origin. Open `https://<workstation-name>.<tailnet-name>.ts.net` from a device connected to your tailnet. Tailscale network access controls determine who can reach the app; everyone with access receives the signed-in Codex user's workspace authority. The container stays on loopback. Serve persists until disabled with `tailscale serve --https=443 off`; the app must also be running. See [deployment operations](specs/deployment_operations.md) for the current workstation URL and verification.

`CODEX_WEBUI_WORKSPACE_ROOT`, `CODEX_WEBUI_CODEX_STATE`, `CODEX_WEBUI_JEV_KEY_FILE`, `CODEX_WEBUI_PORT`, and `CODEX_WEBUI_IMAGE` override defaults. The default external Jev key file is `../jev-pipelines/.env`; its `JEV_API` or `TYPESAFE_API_KEY` value is read as data. Credentials never enter image layers or frontend JavaScript. The container has its own Python, Bash, Git and ripgrep toolchain; only mounted paths are available to Codex.

## Build and verify

Prerequisites: rootless Podman, Python 3.12+ for tooling, and the installed Linux standalone Codex release including `codex-code-mode-host` (tested with 0.160.0). Deno 2.9.7 comes from the pinned tool image. No host Node/npm tooling is used.

```sh
# First install: explicitly authorizes downloading the original locked packages.
./tools/build-image.sh --fetch
# Later source builds reuse the already installed locked dependencies.
./tools/build-image.sh
```

Installation verifies every package against `frontend/package-lock.json` without executing lifecycle scripts. It runs in an ephemeral non-root container. Frontend build, lint and unit tests run in network-disabled containers with scoped Deno permissions. Backend tests and a native App Server new-thread lifecycle check run in the resulting runtime image without credentials or network. New threads explicitly request legacy history because the installed runtime cannot resume its default paginated threads. Existing incompatible conversations show a New chat recovery message; their history is preserved.

```sh
python3 tools/frontend.py check
./tools/generate-app-server-schema.sh
```

Project memory: [specs](specs/_readme.md), [desired design](design/_readme.md), [external interfaces](vendored/_readme.md).

## Gaps

- Real paid Jev → Codex task execution and microphone audio have not been smoke-tested in this project. Tests use transport fixtures; capability discovery is read-only.
- The local image embeds the workstation's standalone Codex binary. ARM64 builds require the matching ARM64 standalone release and separate runtime verification.
- Inherited scheduled tasks and voice sessions retain their existing execution flow; automatic Jev routing applies to submitted text chat messages.

New chat opens a launch page: submit independent prompts without leaving it, then open any of the last ten chats. Spinners show active work and blue dots mark finished unread replies. See [launch behavior](specs/new_chat_launch.md).

Projects now open a scoped quick composer and recent chats. New chat supports No project; creation offers optional workspace details and folder colors. Bottom controls show the recorded last-turn model/effort. See [project launch](specs/project_launch.md).
