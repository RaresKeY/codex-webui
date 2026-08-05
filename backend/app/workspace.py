from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import Any


class UnsafePath(ValueError):
    pass


class Workspace:
    def __init__(self, root: Path, max_file_bytes: int) -> None:
        self.root = root.resolve()
        self.max_file_bytes = max_file_bytes

    def resolve(self, relative: str = ".", *, must_exist: bool = False) -> Path:
        candidate = (self.root / relative).resolve(strict=False)
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise UnsafePath("path escapes the configured workspace root") from exc
        if must_exist and not candidate.exists():
            raise FileNotFoundError(relative)
        return candidate

    def tree(self, relative: str = ".", depth: int = 2) -> dict[str, Any]:
        path = self.resolve(relative, must_exist=True)
        if not path.is_dir():
            raise NotADirectoryError(relative)

        def entry(item: Path, remaining: int) -> dict[str, Any]:
            if item.is_symlink():
                # Never traverse or stat through directory symlinks. Apart from
                # preventing cycles, this keeps an in-root link from exposing an
                # out-of-root directory tree.
                return {
                    "name": item.name,
                    "path": str(item.relative_to(self.root)),
                    "type": "symlink",
                }
            is_dir = item.is_dir()
            result: dict[str, Any] = {
                "name": item.name,
                "path": str(item.relative_to(self.root)),
                "type": "directory" if is_dir else "file",
            }
            if not is_dir:
                stat = item.stat()
                result.update(size=stat.st_size, modified_at=stat.st_mtime)
                result["mime"] = mimetypes.guess_type(item.name)[0]
            elif remaining > 0:
                try:
                    children = sorted(item.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
                    result["children"] = [entry(child, remaining - 1) for child in children[:1000]]
                    result["truncated"] = len(children) > 1000
                except PermissionError:
                    result["unreadable"] = True
            return result

        return entry(path, min(max(depth, 0), 5))

    def read(self, relative: str) -> dict[str, Any]:
        path = self.resolve(relative, must_exist=True)
        if not path.is_file():
            raise IsADirectoryError(relative)
        size = path.stat().st_size
        if size > self.max_file_bytes:
            raise ValueError(f"file exceeds {self.max_file_bytes} byte read limit")
        data = path.read_bytes()
        if b"\x00" in data[:8192]:
            raise ValueError("binary files cannot be read as text")
        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("file is not valid UTF-8 text") from exc
        return {
            "path": str(path.relative_to(self.root)),
            "content": content,
            "size": size,
            "mime": mimetypes.guess_type(path.name)[0] or "text/plain",
        }

    def write(self, relative: str, content: str) -> dict[str, Any]:
        path = self.resolve(relative)
        data = content.encode("utf-8")
        if len(data) > self.max_file_bytes:
            raise ValueError(f"file exceeds {self.max_file_bytes} byte write limit")
        path.parent.mkdir(parents=True, exist_ok=True)
        # Re-resolve after mkdir so a raced symlink cannot redirect the write.
        path = self.resolve(relative)
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags, 0o644)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
        return {"path": str(path.relative_to(self.root)), "size": len(data)}
