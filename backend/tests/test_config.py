from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings, normalize_approval_policy, normalize_sandbox, sandbox_policy


def test_deployment_environment_aliases(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "custom.sqlite3"))
    monkeypatch.setenv("WORKSPACES_ROOT", str(tmp_path / "workspaces"))
    monkeypatch.setenv("IMAGE_LIBRARY_DIR", str(tmp_path / "pictures"))
    monkeypatch.setenv("CODEX_BIN", "/usr/local/bin/codex")
    monkeypatch.setenv("DEFAULT_APPROVAL_POLICY", "never")
    monkeypatch.setenv("DEFAULT_SANDBOX", "readOnly")
    settings = Settings(_env_file=None)
    assert settings.database_path == (tmp_path / "custom.sqlite3").resolve()
    assert settings.workspace_root == (tmp_path / "workspaces").resolve()
    assert settings.image_dir == (tmp_path / "pictures").resolve()
    assert settings.codex_argv == ["/usr/local/bin/codex", "app-server"]
    assert settings.approval_policy == "never"
    assert settings.sandbox == "read-only"


def test_wire_enum_normalization_and_validation(tmp_path: Path) -> None:
    assert normalize_approval_policy("onRequest") == "on-request"
    assert normalize_sandbox("workspaceWrite") == "workspace-write"
    assert sandbox_policy("read-only", tmp_path) == {"type": "readOnly"}
    assert sandbox_policy("danger-full-access", tmp_path) == {"type": "dangerFullAccess"}
    assert sandbox_policy("workspace-write", tmp_path) == {
        "type": "workspaceWrite",
        "writableRoots": [],
        "networkAccess": False,
    }
    with pytest.raises(ValueError, match="approval"):
        normalize_approval_policy("always")
    with pytest.raises(ValueError, match="sandbox"):
        normalize_sandbox("host-root")
