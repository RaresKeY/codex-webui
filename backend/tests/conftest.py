from __future__ import annotations

import sys
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.config import Settings
from app.main import create_app


@pytest.fixture(autouse=True)
def isolate_deployment_environment(monkeypatch):
    # Unit fixtures control their own settings even inside the runtime image.
    for name in tuple(os.environ):
        if name.startswith("CODEX_WEBUI_"):
            monkeypatch.delenv(name)


@pytest.fixture
def workspace_root(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    return root


@pytest.fixture
def settings(tmp_path: Path, workspace_root: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        workspace_root=workspace_root,
        codex_enabled=False,
        allowed_origins=["http://testserver"],
        allowed_hosts=["testserver"],
    )


@pytest.fixture
def client(settings: Settings):
    with TestClient(create_app(settings)) as test_client:
        yield test_client
