ARG CODEX_VERSION=0.145.0

FROM node:22-bookworm-slim AS codex-runtime
ARG CODEX_VERSION
RUN npm install --global "@openai/codex@${CODEX_VERSION}" \
    && npm cache clean --force

FROM node:22-bookworm-slim AS frontend-build
WORKDIR /src/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime

ARG APP_VERSION=0.1.0
ARG CODEX_VERSION=0.145.0
ARG PUID=1000
ARG PGID=1000

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_VERSION=${APP_VERSION} \
    CODEX_VERSION=${CODEX_VERSION} \
    HOME=/data/home \
    CODEX_WEBUI_CODEX_COMMAND="/usr/local/bin/codex app-server" \
    CODEX_HOME=/home/codex/.codex \
    CODEX_WEBUI_DATA_DIR=/data \
    CODEX_WEBUI_WORKSPACE_ROOT=/workspaces \
    CODEX_WEBUI_FRONTEND_DIST=/app/frontend/dist

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates curl git jq ripgrep tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid "${PGID}" codex \
    && useradd --create-home --uid "${PUID}" --gid "${PGID}" --shell /bin/bash codex \
    && mkdir -p /app /data/home /data/images /workspaces /home/codex/.codex \
    && chown -R codex:codex /app /data /workspaces /home/codex

COPY --from=codex-runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=codex-runtime /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/@openai/codex/bin/codex.js /usr/local/bin/codex

WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY --chown=codex:codex backend/ ./backend/
COPY --from=frontend-build --chown=codex:codex /src/frontend/dist ./frontend/dist

USER codex
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
