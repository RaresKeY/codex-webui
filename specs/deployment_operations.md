# Deployment and operations

`tools/build-image.sh` builds `localhost/codex-webui-2-tools:local`, verifies frontend build/lint/tests through the non-root tool container, builds `localhost/codex-webui-2:local`, and runs backend tests and a real App Server thread-lifecycle check in the runtime image without network/auth mounts. The lifecycle check creates only temporary state and makes no inference calls. `--fetch` explicitly allows dependency download, using exact integrity-checked lockfile tarballs and no lifecycle scripts. Routine frontend checks disable network and Deno remote-module resolution.

`Containerfile.tools` pins Python 3.12 and Deno 2.9.7 image digests. The runtime pins the Python base and `backend/requirements.lock.txt`, copies only app source and the current validated `frontend/dist`, and obtains standalone Codex/codex-code-mode-host from an explicit build context pointing to the installed release's bin directory. No `.codex`, `.env`, data or auth directory enters the context. apt toolchain packages remain repository-resolved.

`tools/run-container.sh` runs rootless Podman with the host numeric identity, dropped capabilities and no-new-privileges. It publishes `127.0.0.1:8766`, uses app data in `codex-webui-2-data`, mounts existing Codex state at `/codex`, preserves the selected workspace's host absolute path inside the container, and mounts one Jev key file read-only when present. It passes the canonical host Jev and Codex-state paths through `CODEX_WEBUI_JEV_KEY_SOURCE_FILE` and `CODEX_WEBUI_CODEX_STATE_SOURCE_DIR` so workspace browser routes cannot expose their original mounts. It does not inspect credentials, expose the Podman socket, replace an existing named container, or open a visible browser window. Use `--detach` for background launch and `podman stop codex-webui-2` to stop it; foreground launch stops with Ctrl-C. The container is removed and data retained. Runtime builds use Docker image format to preserve the HTTP health check.

Optional `tools/run-local.sh` serves the same built frontend on loopback using a project-local Python environment. The container launcher is primary. Schema generation and capability probes are read-only; live task/approval smoke remains explicit opt-in.

Private remote access is opt-in with `tools/run-container.sh --detach --tailscale`. The launcher requires a running Tailscale connection, obtains its canonical `.ts.net` DNS name, and adds exactly that Host and HTTPS origin alongside localhost. It does not configure Tailscale or broaden the container's loopback bind. On the host, `tailscale serve --bg --yes --https=443 http://127.0.0.1:8766` configures private HTTPS reverse proxying; administrator access may be required. Serve owns TCP 443 on the tailnet, supports browser WebSockets, and persists until `tailscale serve --https=443 off`. No Funnel, LAN listener, router forwarding, or public domain is used. The container still requires a running launcher; automatic startup is not configured.

Generated distribution files are temporary current candidates. Retain the user-requested local image, not archives or accumulated older builds. No registry publication is requested or configured.

Source hosting uses the project’s public origin. Authentication and any additional remotes belong in local Git configuration, outside committed project documentation.

Both image builds explicitly mark final images `io.rareskey.retention=retain`, intermediate build images `ephemeral`, and project ownership `codex-webui-2`. The build flow holds a shared workstation build-retention flock so periodic cleanup cannot race these builds.

## Experimental browser

For the experimental browser, install the rendered `tools/browser-bridge.service.in` as a user service, with `@PROJECT_ROOT@` replaced by the owning checkout path. Start it before `tools/run-container.sh --detach --tailscale --browser`. The bridge uses the installed user Flatpak and project Python environment; its private Unix socket is mounted read-only into the container. `CODEX_WEBUI_CONTAINER_NAME`, `CODEX_WEBUI_PORT` and `CODEX_WEBUI_DATA_VOLUME` allow an isolated candidate runtime. The default preserves the existing data volume and loopback port. Roll back by stopping the candidate and relaunching the retained previous image against the same data volume; omit `--browser` when the image predates the bridge. See [browser_integration.md](browser_integration.md).

## Runtime retention

The owning build wrapper explicitly labels final runtime/toolchain images as retained and intermediate images as ephemeral, with `codex-webui-2` project ownership. Builds hold the shared workstation retention lock; reviewed cleanup holds it exclusively and refuses active coordinated or uncoordinated builds.

Keep the deployed runtime, the current tools image, an active candidate and one verified previous runtime tagged `localhost/codex-webui-2:rollback`. After deployment verification, older `before-*` snapshots and superseded untagged project runtimes are no longer required rollback images unless the user explicitly reserves them. Rotate the single rollback before deleting obsolete exact IDs. Classify by inspected image ID/labels rather than tag names alone; preserve the complete parent-image closure of all retained images and every container reference.

Remove completed project-owned ephemeral intermediates by exact ID after reference/dependency/task checks. No stopped-container cleanup is implied for unrelated work. Never force deletion, prune volumes, use unrestricted system/image prune or manually modify container storage. Volumes, authentication, the dedicated browser profile and non-reproducible source/evidence survive cleanup. The global weekly timer removes only labeled dangling ephemeral images older than seven days; it does not replace review of tagged snapshots or unlabeled images. Unknown ownership remains a separate audit.

## Gaps

- amd64 image/runtime is the current target; no ARM64 image/runtime evidence yet.
- apt packages are not snapshot-pinned, and the selected standalone binary is local rather than automatically fetched.
- No application-specific remote authentication, registry release process or versioned data migration is included; private access relies on Tailscale network admission and its access controls.
