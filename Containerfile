FROM docker.io/library/python:3.12-slim@sha256:7a8b475003c4fe15a2cd4e55e5cfc2f3560bdc9333d624f24cdd6d4340fd7a17
ARG PUID=1000
ARG PGID=1000
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates git ripgrep bash tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid ${PGID} webui && useradd --uid ${PUID} --gid ${PGID} --create-home --shell /bin/bash webui \
    && mkdir -p /app /data /codex /workspaces && chown webui:webui /app /data /codex /workspaces
WORKDIR /app
COPY backend/requirements.lock.txt /app/requirements.lock.txt
RUN pip install --no-cache-dir -r /app/requirements.lock.txt
# The build script supplies only the installed standalone release's bin directory.
COPY --from=codex-runtime /codex /usr/local/bin/codex
COPY --from=codex-runtime /codex-code-mode-host /usr/local/bin/codex-code-mode-host
COPY --chown=webui:webui backend/app /app/backend/app
COPY --chown=webui:webui frontend/dist /app/frontend/dist
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    CODEX_HOME=/codex CODEX_WEBUI_CODEX_COMMAND="/usr/local/bin/codex app-server" \
    CODEX_WEBUI_DATA_DIR=/data CODEX_WEBUI_WORKSPACE_ROOT=/workspaces \
    CODEX_WEBUI_FRONTEND_DIST=/app/frontend/dist CODEX_WEBUI_RUNTIME=container
USER webui
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
