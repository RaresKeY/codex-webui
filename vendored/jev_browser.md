# Jev browser port and Chromium boundary

## Source and ownership

The project-owned Python browser mechanics and DOM observer were ported from the local `jev-browser-agent` checkout at commit `dcdb24c43ae43d513caec3a7efd2a44d3a05a156`. Owning sources are `backend/app/jev_browser/browser.py`, `core.py`, and `observer.js`; orchestration is `backend/app/browser_service.py`. The source checkout was read-only during this port. No external Jev SDK/model dependency is added.

Only the launch/audit, private CDP pipe transport and observed-control mechanics are carried over. Task-specific effect authorization, inference, history/reporting and image downloads are excluded. The profile/lock namespace is changed to `codex-webui-browser`; target preparation and geometry are added for visible pointer movement. The source project has no license declaration; this local project-owned port does not add a project license.

The runtime requires the already installed user Flatpak `io.github.ungoogled_software.ungoogled_chromium`. It preserves the original audit and denial flags, Chromium sandboxing, TLS verification, muted headless rendering, shared network and DRI device access. There is no downloaded browser or TCP debugging port. Primary upstream interfaces are [Chromium DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/) and [Flatpak command reference](https://docs.flatpak.org/en/latest/flatpak-command-reference.html). Chromium is BSD-3-Clause; Flatpak is LGPL-2.1-or-later. Distribution does not bundle these installed runtimes.

## Gaps

- Flatpak application/browser versions are installed-machine state, not pinned by this repository; permission drift fails closed.
- The original Flatpak contract was verified on this Linux workstation. It is not a claim of Mac, container, arm64 or real-site compatibility.
- Recheck the effective permission audit and CDP compatibility after browser or Flatpak upgrades.
