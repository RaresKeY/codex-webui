# Runtime dependencies

Distributed dependencies use committed lockfiles or immutable digests. `backend/requirements.txt` currently constrains FastAPI 0.116–<1, Uvicorn 0.35–<1, pydantic-settings 2.10–<3, eval-type-backport 0.3–<1, aiosqlite 0.21–<1, python-multipart 0.0.20–<1, APScheduler 3.11–<4, pytest 8.4–<9, pytest-asyncio 1.1–<2, and HTTPX 0.28–<1. The backport lets Pydantic evaluate the repository's modern union annotations on macOS system Python 3.9. Python production and test dependencies are not yet split or hash-locked.

`frontend/package.json` and `package-lock.json` pin the direct JavaScript dependencies. The current top-level install includes React/React DOM 19.2.8, lucide-react 1.28.0, Vite 8.2.0, TypeScript 6.0.3, Vitest 4.1.10, ESLint 10.8.0, and exact related plugin/type versions.

The primary Mac launcher uses host Python 3 plus a project-local `.venv`, host Node/npm for frontend builds, and prefers the official standalone Codex executable at `~/.local/bin/codex` unless `CODEX_BIN` explicitly selects another binary. The optional runtime image is based on `python:3.12-slim` and copies Node from `node:22-bookworm-slim`; build stages and apt packages are not pinned to immutable digests.

GitHub Actions uses `actions/checkout`, language setup actions, and Docker's QEMU, Buildx, metadata, login, and build/push actions. The GHCR publishing job grants `packages: write` only at that job boundary and authenticates with the repository-scoped `GITHUB_TOKEN`; these action references currently track major-version tags rather than immutable commits.

Lockfiles are version truth; this note records rationale; `THIRD_PARTY_NOTICES.md` carries notices. Python owns orchestration. Native dependencies need a real library requirement or benchmark and both architectures or a fallback.

## Gaps

- Hash-lock Python production dependencies separately from tests and pin base images/distro packages appropriately.
- Generate the complete transitive version/license inventory and add vulnerability, lock-integrity, and architecture checks.
- Pin GitHub Actions to reviewed commit SHAs before treating the publishing workflow as a hardened release pipeline.
