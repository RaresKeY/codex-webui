# Security

Anyone who can use Codex Web UI may gain the effective Codex authority of the signed-in Mac user over configured workspaces and Codex state. The optional container mode instead has the container user's mounted authority.

For initial deployment:

- use `tools/run-mac.sh`, which refuses a non-loopback host;
- set `CODEX_WEBUI_WORKSPACE_ROOT` to the narrowest useful ancestor;
- grant microphone access only when using realtime voice and stop the session when finished;
- for optional Compose use, set absolute `CODEX_WORKSPACES` to the narrowest useful ancestor;
- mount only that selected workspace root and runtime Codex state in container mode;
- run as a non-root UID/GID matching host file ownership;
- never mount the Docker socket, host root, or broad home directory;
- use Tailscale ACLs plus an authenticating proxy before remote use;
- keep logs free of prompts, outputs, files, tokens, and environment values;
- confirm destructive actions and privileged Codex operations.

The current loopback baseline enforces trusted Host values, configured/same-origin browser writes and WebSockets, and CSP, microphone policy, frame denial, MIME-sniffing prevention, and no-referrer headers. These controls are not user authentication. Tailscale or any other remote exposure still needs an authenticated identity boundary and rate limiting.

Report vulnerabilities privately to the repository owner. Do not publish credentials, exploit details, private prompts, or workspace data.

## Gaps

- Publish a private security contact and response expectations.
- Add authentication and rate limiting before remote exposure; explicit CSRF tokens may be needed once cookie-based remote sessions exist.
- Close the workspace ancestor-component read/write TOCTOU window and extend hostile-content/browser security tests.
