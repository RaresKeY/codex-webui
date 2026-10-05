# Deployment and operations

`tools/build-image.sh` builds `localhost/codex-webui-2-tools:local`, verifies frontend build/lint/tests through the non-root tool container, builds `localhost/codex-webui-2:local`, and runs backend tests and a real App Server thread-lifecycle check in the runtime image without network/auth mounts. The lifecycle check creates only temporary state and makes no inference calls. `--fetch` explicitly allows dependency download, using exact integrity-checked lockfile tarballs and no lifecycle scripts. Routine frontend checks disable network and Deno remote-module resolution.

`Containerfile.tools` pins Python 3.12 and Deno 2.9.7 image digests. The runtime pins the Python base and `backend/requirements.lock.txt`, copies only app source and the current validated `frontend/dist`, and obtains standalone Codex/codex-code-mode-host from an explicit build context pointing to the installed release's bin directory. No `.codex`, `.env`, data or auth directory enters the context. apt toolchain packages remain repository-resolved.

`tools/run-container.sh` runs rootless Podman with the host numeric identity, dropped capabilities and no-new-privileges. It publishes `127.0.0.1:8766`, uses app data in `codex-webui-2-data`, mounts existing Codex state at `/codex`, preserves the selected workspace's host absolute path inside the container, and mounts one Jev key file read-only when present. It does not inspect credentials, expose the Podman socket, replace an existing named container, or open a visible browser window. Use `--detach` for background launch and `podman stop codex-webui-2` to stop it; foreground launch stops with Ctrl-C. The container is removed and data retained. Runtime builds use Docker image format to preserve the HTTP health check.

Optional `tools/run-local.sh` serves the same built frontend on loopback using a project-local Python environment. The container launcher is primary. Schema generation and capability probes are read-only; live task/approval smoke remains explicit opt-in.

Generated distribution files are temporary current candidates. Retain the user-requested local image, not archives or accumulated older builds. No registry publication is requested or configured.

## Gaps

- amd64 image/runtime is the current target; no ARM64 image/runtime evidence yet.
- apt packages are not snapshot-pinned, and the selected standalone binary is local rather than automatically fetched.
- No remote authentication, registry release process or versioned data migration is included.
