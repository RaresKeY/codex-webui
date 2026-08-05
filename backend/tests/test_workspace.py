from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.workspace import UnsafePath, Workspace


def test_rejects_parent_traversal(workspace_root: Path) -> None:
    workspace = Workspace(workspace_root, 1024)
    with pytest.raises(UnsafePath):
        workspace.read("../secret.txt")
    with pytest.raises(UnsafePath):
        workspace.write("a/../../secret.txt", "no")


def test_text_round_trip_and_binary_guard(workspace_root: Path) -> None:
    workspace = Workspace(workspace_root, 1024)
    assert workspace.write("src/main.py", "print('ok')\n")["size"] == 12
    assert workspace.read("src/main.py")["content"] == "print('ok')\n"
    (workspace_root / "binary.dat").write_bytes(b"hello\x00world")
    with pytest.raises(ValueError, match="binary"):
        workspace.read("binary.dat")


def test_tree_does_not_follow_symlink_outside_root(workspace_root: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret")
    link = workspace_root / "escape"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks are not available on this platform")

    result = Workspace(workspace_root, 1024).tree(".", depth=3)
    escape = next(child for child in result["children"] if child["name"] == "escape")
    assert escape == {"name": "escape", "path": "escape", "type": "symlink"}
    assert "children" not in escape
    with pytest.raises(UnsafePath):
        Workspace(workspace_root, 1024).read("escape/secret.txt")

