# Experimental Jev browser integration

## Status

Experimental Linux browser companion with an optional Unix-socket bridge for the container deployment. No private Desktop API or remote debugging endpoint.

## Source Sync

- `backend/app/browser_service.py`: typed actions, thread ownership, serialization, bounded frame/observation projection and tool handler.
- `backend/app/jev_browser/`: restricted Flatpak launch/audit, CDP pipe transport and repository-owned DOM observer, ported from Jev.
- `backend/app/codex_client.py` and `main.py`: public dynamic-tool registration/dispatch, scoped events and browser HTTP routes.
- `frontend/src/BrowserContext.tsx`, `App.tsx`, `api.ts`, `browser-chrome.css`, and `styles.css`: live view, browser chrome, panel auto-open and cursor presentation.
- `backend/tests/test_browser.py`, `frontend/src/api.test.ts`, and `tools/smoke_browser.py`: adapter, isolation and real synthetic browser checks.

## Behavior

`CODEX_WEBUI_BROWSER_ENABLED` defaults to true on this experimental branch. Availability requires the Linux `localhost-companion` runtime and installed Flatpak. Actual launch additionally requires the Chromium application and a successful effective-permissions audit; failure never falls back to a host browser. A container may use `CODEX_WEBUI_BROWSER_BRIDGE_SOCKET` to connect to the audited host service. Other runtimes show the limitation.

New threads register the function dynamic tool `browser` only for the verified `codex-cli 0.160.1`. Other versions retain the existing protocol subset. Resume does not add tools to existing threads. Tool operations run asynchronously so browser activity cannot block the App Server response reader. Results contain bounded untrusted page text, observation version and node IDs; full link destinations and form actions are omitted. No Jev inference provider, paid retry loop, or task-effect engine is ported.

Accepted actions are open, observe, click, type, scroll, back, reload and close. Navigation accepts HTTPS without embedded credentials and rejects direct localhost addresses; it does not provide a network firewall or DNS/IP isolation. Click/type require the latest observation version and observed target; the observer rechecks the document, element identity, visibility and reachability. The agent tool accepts no arbitrary JavaScript, selectors, coordinates, commands or file paths. A separate human-only input contract accepts bounded viewport clicks, text, fixed keys and vertical wheel input; it is not in the dynamic tool schema. Password/file fields and input values are excluded. Downloads are denied, dialogs dismissed and extra page targets closed. Typing is limited to 2,000 characters and scrolling is downward in the main document.

The companion owns at most one browser session, scoped to its opening thread, with a dedicated persistent profile and advisory lock. Closing the panel preserves the session; closing the browser tab or shutting down the companion terminates it. A second conversation must close the first session before opening another. Browser profiles are outside Git and no existing Jev/host cookies are imported. Site cookies and local storage use the same dedicated profile across session close, companion restart and app deployment. Persistent-cookie survival is smoke-tested across a clean browser shutdown/reopen. Cookie values are never returned by an API or copied into app state; site expiry remains authoritative. There are no database changes or migrations; rollback is disabling the flag or returning to the prior branch, with the separate profile left outside project state.

`GET/POST /api/threads/{thread_id}/browser` and `POST /api/threads/{thread_id}/browser/input` inherit the application's Host/origin boundary. Frames are JPEGs bounded to 3 MB of base64, returned with `Cache-Control: no-store`, kept only in memory and never sent through shared App Server event queues. The visible view requests a frame about every 650 ms; polling captures only and preserves agent node references. It stops when the panel unmounts. The fixed page viewport is 1280×900 and scales to the available panel width. Page pixels accept direct human input when Control is on: scaled clicks map to the fixed 1280×900 viewport (including iframe controls), keyboard/paste input targets the remotely focused field, and wheel input scrolls the remote page. Escape forwards the key and releases local keyboard focus. A text entry row supports phone keyboards. View only disables page input. Navigation, back, reload and close remain available. Input is serialized with agent actions under the session lock, invalidates agent observations, and returns a new frame. The frontend queues at most 100 input packets, batches adjacent text and aborts/discards queued input on pane exit; failed operations are never retried automatically. Input text is never included in activity events or logs.

`webui/browser` events carry thread identity, activity and pointer coordinates. Agent actions open/select Browser automatically; frame/pointer updates do not reopen a manually hidden panel. The panel uses the single saved width shared with every other context tab; at narrow widths it uses the existing overlay and closes the left drawer. The cursor begins in the page center, moves to the observed target over 420 ms, then displays click feedback. Reduced motion disables cursor transitions/pulses. Motion and screenshots represent the real controlled page; there is no simulated external webpage.

## Container bridge

`backend/app/browser_bridge.py` exposes only typed browser actions, separate human input, bounded frames, health and frame-free activity over a Unix socket. `tools/run-browser-bridge.sh` uses the project Python environment and installed user Flatpak; `tools/browser-bridge.service.in` is the user-service template. Its runtime directory is mode 0700 and its socket is created under umask 077. The container launcher `--browser` mounts that directory read-only; neither host D-Bus nor Podman control sockets are exposed. One bridge belongs to one backend. Stopping the backend closes its sessions; a disconnected action client cancels pending work. Event transport may reconnect, but actions never retry automatically.

Deployments must start the host bridge before starting the container. Browser dynamic tools are registered only on newly created chats. Disabling the bridge or rolling back the image restores the earlier deployment without data migrations. The separate browser profile remains outside app data.

## Verification

The original implementation pass passed 58 backend tests and 43 frontend tests. The local-work integration is verified separately in `verification.md`, with the retained theme, launch flow and Jev process.

- Backend tests cover URL rejection, schema validation, disabled runtime, cross-site writes, thread isolation, stale observations, polling stability, pointer ordering, supported-version registration and nonblocking dynamic-tool dispatch.
- `tools/smoke_browser.py --run` launches the audited Flatpak against a synthetic loopback fixture through the test-only allowlist browser; it uses a temporary isolated profile/lock, removes its profile after closing, and checks real screenshot, click/type, cursor events and password omission without external sites or inference.
- A redacted live CLI 0.160.1 ephemeral-thread smoke verified registration and a real agent turn invoking open/click against the synthetic fixture, with unchanged Codex config digest.
- Production UI checked at 1920×1080 and 760×900: initial collapse, automatic Browser selection/opening, separate panel geometry, narrow fit, resize collapse, drawer exclusivity, reachable close control, measured cursor intermediate positions and reduced-motion media behavior.

## Integrated pane presentation

The visible Browser sits in the flush context region with square outer edges, a neutral conversation divider and compact aligned pane controls. At narrow widths it attaches directly to the screen edges; automatic opening, frame cadence and cursor motion retain their existing behavior.

Closing or switching away from a browser pane aborts its pending client action. A synchronous guard prevents duplicate actions, and generation checks discard frame responses predating a completed action. Event streams back off for one second on clean EOF as well as transport failure, avoiding a tight reconnect loop.

The browser address bar accepts bare domains and protocol-relative addresses, adding HTTPS before submission. Explicit HTTP(S) protocols remain unchanged for backend validation; invalid or credential-bearing addresses are rejected. Native URL input validation cannot block bare-domain submission.

Browser chrome lives in `browser-chrome.css`: an inset active tab, grouped back/reload controls and a rounded address field with an icon submit control. Long titles truncate, focus remains visible, and coarse-pointer controls enlarge. The empty tab directs users to the address field; browser controls expose only supported actions.

## Gaps

- The page is a periodically refreshed screenshot, with bounded human click/key/text/wheel input; drag selection, multi-touch, multiple tabs, uploads, downloads, popup/frame workflows and mobile page emulation are absent.
- Browser action authorization relies on agent adherence to explicit user instructions, not Jev's original exact task/effect allowlists. The browser has independent network authority from the Codex process sandbox.
- Session cookies without site expiry may expire on browser shutdown; there is no cookie-export API or forced expiry extension.
- Real-site/login reliability, Linux arm64 hardware and Mac runtime support remain unverified or unsupported. Profile storage uses Chromium's basic password store and is not keyring encrypted.
- There is no durable event replay or automatic profile pruning. A lost action event may require manually reopening the panel.
