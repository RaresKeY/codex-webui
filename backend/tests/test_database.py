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


@pytest.mark.asyncio
async def test_turn_selections_survive_reopen_without_relabeling_previous_turns(tmp_path: Path) -> None:
    path = tmp_path / "selections.sqlite3"
    db = Database(path)
    await db.initialize()
    await db.record_turn_selection("chat", "first", "gpt-6-luna", "low")
    await db.record_turn_selection("chat", "second", "gpt-6.1-sol", "high")
    reopened = Database(path)
    await reopened.initialize()
    assert await reopened.turn_selections("chat") == {
        "first": {"model": "gpt-6-luna", "effort": "low"},
        "second": {"model": "gpt-6.1-sol", "effort": "high"},
    }
    assert await reopened.turn_selections("other") == {}

@pytest.mark.asyncio
async def test_latest_turn_labels_are_bounded_to_requested_threads(tmp_path: Path) -> None:
    db = Database(tmp_path / "latest.sqlite3")
    await db.initialize()
    await db.record_turn_selection("chat", "first", "gpt-6.1-sol", "high")
    await db.record_turn_selection("chat", "second", "gpt-6-luna", "low")
    await db.record_turn_selection("other", "t1", "gpt-6.1-sol", "medium")
    assert await db.latest_turn_selections([]) == {}
    assert await db.latest_turn_selections(["chat", "missing"]) == {"chat": {"last_turn_model": "gpt-6-luna", "last_turn_effort": "low"}}
