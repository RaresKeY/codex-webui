from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.database import Database


@pytest.mark.asyncio
async def test_project_workspace_column_migrates_existing_database(tmp_path: Path) -> None:
    path = tmp_path / "old.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute(
        """CREATE TABLE projects (
        id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
        color TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""
    )
    connection.commit()
    connection.close()
    db = Database(path)
    await db.initialize()
    columns = await db.fetchall("PRAGMA table_info(projects)")
    assert "workspace" in {column["name"] for column in columns}
    await db.initialize()

