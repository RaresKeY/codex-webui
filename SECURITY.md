# Security

Anyone who can use Codex Web UI may gain the effective authority of the container over mounted workspaces and Codex state.

For initial deployment:

- bind only to `127.0.0.1`;
- set absolute `CODEX_WORKSPACES` to the narrowest useful ancestor; Compose mounts it at the identical absolute target;
- mount only that selected workspace root and runtime Codex state;
- run as a non-root UID/GID matching host file ownership;
- never mount the Docker socket, host root, or broad home directory;
- use Tailscale ACLs plus an authenticating proxy before remote use;
- keep logs free of prompts, outputs, files, tokens, and environment values;
- confirm destructive actions and privileged Codex operations.

The current loopback baseline enforces trusted Host values, configured/same-origin browser writes and WebSockets, and CSP, frame denial, MIME-sniffing prevention, and no-referrer headers. These controls are not user authentication. Tailscale or any other remote exposure still needs an authenticated identity boundary and rate limiting.

Report vulnerabilities privately to the repository owner. Do not publish credentials, exploit details, private prompts, or workspace data.

## Gaps

- Publish a private security contact and response expectations.
- Add authentication and rate limiting before remote exposure; explicit CSRF tokens may be needed once cookie-based remote sessions exist.
- Close the workspace ancestor-component read/write TOCTOU window and extend hostile-content/browser security tests.
