# Security

The loopback app has the authority of its Codex process over mounted workspaces and state. `tools/run-container.sh` publishes only 127.0.0.1, runs non-root, drops capabilities, and mounts the selected workspace, existing Codex state, app data volume and one external read-only Jev credential file. It never mounts the Podman socket or embeds credentials into an image.

Jev receives the exact current ask over HTTPS. Credentials stay in the Python companion. Responses must use the pinned Jev model, exact typed questions, allowed choices, finite normalized probabilities and a consistent maximizing Choice. Routing/model-change failure prevents ask submission. No automatic retries or raw provider-error bodies are exposed.

Existing trusted Host/Origin checks, CSP, microphone policy, WebSocket origin checks, canonical workspace containment and Codex-owned approvals remain. Workspace access is bounded to configured mounts. No remote deployment or authentication is implemented.

## Gaps

- Add authentication before any remote exposure.
- The inherited workspace adapter has an ancestor-component TOCTOU gap under hostile concurrent filesystem changes.
- Jev is an uncalibrated model/effort adviser; it does not authorize actions or establish task success.
