# Codex WebUI 2

A separate, local Codex chat app with a quieter ChatGPT-style interface. It reuses the original `../codex-webui` backend, native thread history, approvals, workspace tools, projects, schedules, images, and experimental voice adapter. The original checkout is unchanged.

One sidebar, readable conversations, user message bubbles, a compact composer, and optional workspace tools keep chat central. Command output and public thought summaries expand on demand. Desktop navigation collapses; phone navigation and context use exclusive drawers.

Every text message follows this order:

1. Send the original ask to Jev (`jev-1.13.0`) using the task router's V5 policy.
2. Validate and select `gpt-6.1-sol` or `gpt-6-luna` and low/medium/high/xhigh/max effort.
3. Send the selected model to Codex with `thread/resume` and await acknowledgement.
4. Send the unchanged ask through `turn/start` with that model and effort.

Jev failure, an invalid decision, or a rejected model change stops submission. There is no silent fallback or automatic retry. Failed drafts remain in the composer. Jev receives only the current ask; it receives no history, source files, account metadata, or credentials from Codex. Its confidence estimates are uncalibrated.

## Container launch

The built image is `localhost/codex-webui-2:local`:

```sh
./tools/run-container.sh --detach
```

Open **http://127.0.0.1:8766**. The launcher runs rootless Podman, publishes loopback only, mounts the workspace at its identical absolute path, mounts existing Codex state externally, and uses the separate `codex-webui-2-data` volume. It does not open a browser window.

`CODEX_WEBUI_WORKSPACE_ROOT`, `CODEX_WEBUI_CODEX_STATE`, `CODEX_WEBUI_JEV_KEY_FILE`, `CODEX_WEBUI_PORT`, and `CODEX_WEBUI_IMAGE` override defaults. The default external Jev key file is `../jev-pipelines/.env`; its `JEV_API` or `TYPESAFE_API_KEY` value is read as data. Credentials never enter image layers or frontend JavaScript. The container has its own Python, Bash, Git and ripgrep toolchain; only mounted paths are available to Codex.

## Build and verify

Prerequisites: rootless Podman, Python 3.12+ for tooling, and the installed Linux standalone Codex release including `codex-code-mode-host` (tested with 0.160.0). Deno 2.9.7 comes from the pinned tool image. No host Node/npm tooling is used.

```sh
# First install: explicitly authorizes downloading the original locked packages.
./tools/build-image.sh --fetch
# Later source builds reuse the already installed locked dependencies.
./tools/build-image.sh
```

Installation verifies every package against `frontend/package-lock.json` without executing lifecycle scripts. It runs in an ephemeral non-root container. Frontend build, lint and unit tests run in network-disabled containers with scoped Deno permissions. Backend tests run in the resulting runtime image without credentials or network.

```sh
python3 tools/frontend.py check
./tools/generate-app-server-schema.sh
```

Project memory: [specs](specs/_readme.md), [desired design](design/_readme.md), [external interfaces](vendored/_readme.md).

## Gaps

- Real paid Jev → Codex task execution and microphone audio have not been smoke-tested in this project. Tests use transport fixtures; capability discovery is read-only.
- The local image embeds the workstation's standalone Codex binary. ARM64 builds require the matching ARM64 standalone release and separate runtime verification.
- Inherited scheduled tasks and voice sessions retain their existing execution flow; automatic Jev routing applies to submitted text chat messages.
