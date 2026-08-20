# Codex Web UI

A local Mac client for the open-source Codex CLI. A loopback-only companion owns one `codex app-server` subprocess, inherits the normal Codex login, serves the React client, and keeps the browser away from CLI state and subprocess control.

Project memory is split deliberately:

- [`specs/`](specs/_readme.md): current implemented behavior and verification.
- [`design/`](design/_readme.md): desired current and future design.
- [`vendored/`](vendored/_readme.md): external interfaces and dependencies.

## Mac quick start

Prerequisites:

- macOS with Python 3;
- Codex CLI installed and already signed in (`codex login` only if needed);
- Node.js with npm or pnpm for the first frontend build (`brew install node` is one option).

Start the client:

```bash
./tools/run-mac.sh
```

The launcher creates a project-local Python environment, builds the frontend, starts the companion on `http://127.0.0.1:8765`, and opens that address. App-owned data defaults to `~/Library/Application Support/Codex WebUI`; the workspace root defaults to this checkout's parent directory.

The companion launches the host `codex app-server` over stdio without setting a replacement `CODEX_HOME`, so Codex resolves the same login and state as the CLI. It never copies credentials into the project or browser. It binds only to loopback and refuses a non-loopback host.

When present, the launcher prefers the official standalone installation at `~/.local/bin/codex` over a copy bundled inside another desktop app. Update that installation with the official command:

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
```

Useful overrides:

```bash
CODEX_BIN=/absolute/path/to/codex \
CODEX_WEBUI_WORKSPACE_ROOT=/Users/me/workspace \
CODEX_WEBUI_PORT=8765 \
CODEX_WEBUI_OPEN_BROWSER=0 \
./tools/run-mac.sh
```

The Mac launcher enables the App Server's listed `realtime_conversation` feature only for its child process using Codex's documented `--enable` flag. Set `CODEX_WEBUI_REALTIME_FEATURE_ENABLED=false` to omit that launch override; no `config.toml` change is needed.

Omit `CODEX_WEBUI_OPEN_BROWSER=0` when the launcher should open the localhost URL in the macOS default external browser. Set it to `0` when using Codex's in-app Browser or opening the page manually.

## Implemented Codex surface

- list, search, read, create, resume, name, archive, and fork native Codex threads;
- start, steer, interrupt, and stream turns and item deltas;
- inline command and file-change approvals with exact current decision values;
- account, model, usage, and context-window reporting;
- browser microphone/audio using the public experimental realtime protocol when the installed App Server reports it usable;
- a contextual panel backed by Outputs, read-only background-terminal activity, related Codex threads, bounded workspace Explorer, and read-only Git changes. Browser remains visibly planned because it has no public App Server method.

Realtime voice follows the App Server WebRTC flow: the browser creates the microphone track and `oai-events` data channel, sends its SDP offer through the companion using `thread/realtime/start`, receives `thread/realtime/sdp` over the existing thread event socket, and applies the answer to its `RTCPeerConnection`. The client selects documented WebRTC version `v3`; App Server version `v2` is deliberately rejected because the public protocol does not support it over WebRTC. The companion enables the listed experimental feature at launch, then requires the live App Server to confirm the feature, a suitable signed-in state when the provider requires one, and a non-empty voice catalog before enabling the microphone. ChatGPT-authenticated WebRTC remains inside App Server; no API key or OAuth material is sent to browser JavaScript.

The UI also retains the existing project organization, schedule, image-library, usage, and workspace-browser features. Codex remains authoritative for authentication, execution, thread history, sandboxing, and approvals.

## Protocol compatibility

This pass was implemented and tested against the official standalone `codex-cli 0.147.0`. Generate that executable's complete public schema without touching configuration:

```bash
./tools/generate-app-server-schema.sh
```

Generated files go under ignored `tmp/app-server-schema/`. The small frontend type subset in `frontend/src/app-server-protocol.ts` records the exact version used for the implemented methods.

Run the opt-in live smoke after signing in. It creates an ephemeral read-only thread, requests one command approval, denies it, verifies the command made no change, and compares the Codex `config.toml` digest before and after:

```bash
.venv/bin/python tools/smoke_app_server.py
```

Probe the launch-scoped realtime feature, signed-in state, and voice inventory without starting a realtime session or requesting microphone permission:

```bash
.venv/bin/python tools/probe_realtime_capability.py
```

## Development

Install backend dependencies in a virtual environment, then run all checks:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
PYTHON_BIN=.venv/bin/python ./tools/validate.sh
```

Visible changes still need desktop and narrow-width browser checks until browser automation is added.

## Optional Linux container

The earlier Docker/Compose deployment remains available for Linux and Raspberry Pi work:

```bash
./tools/bootstrap.sh
```

It binds `127.0.0.1:8765`, mounts the selected workspace and file-backed Codex state, and runs Codex inside the container. That mode sees the container toolchain rather than the Mac host toolchain and is not the primary realtime-voice target. See [`specs/deployment_operations.md`](specs/deployment_operations.md) before using or publishing the container image.

## Security

Anyone who can use this loopback client gains the effective Codex authority of the signed-in Mac user over configured workspaces. Do not expose the port to a LAN or the internet. The current Host, Origin, fetch-site, CSP, framing, MIME, referrer, and microphone policies are a localhost baseline, not user authentication.

## Gaps

- Add automated browser/WebRTC integration coverage and manual microphone/audio evidence on a signed-in account.
- Add a macOS launch agent or signed `.app` wrapper if background startup and Dock integration become requirements.
- Reconcile or retire the older container distribution after deciding whether Mac-only is the permanent product scope.
