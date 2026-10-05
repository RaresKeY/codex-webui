# Runtime dependencies

React/TypeScript/Vite/lucide-react/react-markdown/remark-gfm and test/lint dependencies are inherited unchanged from `../codex-webui/frontend/package-lock.json`. Direct pinned versions and transitive integrities remain authoritative. `tools/frontend.py` extracts exact locked tarballs inside an ephemeral non-root container; no lifecycle scripts execute and no package executor is used. Build/lint/test use Deno 2.9.7 with scoped filesystem/FFI/system permissions and disabled container network. Vitest 4.1.10 uses an explicit custom fork pool and `tools/deno-worker.py` to preserve those permissions in child workers; Deno's default Node-compatible fork adds unrestricted `-A`. Worker-thread teardown is not supported sufficiently by this Deno release.

`Containerfile.tools` pins the official Deno 2.9.7 and Python base digests. `backend/requirements.lock.txt` freezes the tested Python graph. The runtime embeds the installed standalone Linux Rust Codex release and its code-mode helper, tested with 0.160.0; it contains no Node runtime. Python owns orchestration and Jev HTTPS uses the standard library.

References: [Deno container workflow](https://docs.deno.com/runtime/reference/docker/) and [Codex App Server](https://learn.chatgpt.com/docs/app-server).

## Gaps

- The custom pool uses the pinned Vitest fork implementation and needs compatibility review when Vitest changes.
- apt packages lack snapshot pins and Python packages lack per-wheel hashes.
- The local Codex standalone release is supplied by the build script; remote automatic installation is intentionally absent.
