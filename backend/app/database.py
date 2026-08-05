from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiosqlite

from .models import utc_now


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  color TEXT,
  workspace TEXT NOT NULL DEFAULT '.',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chat_metadata (
  thread_id TEXT PRIMARY KEY,
  project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
  pinned INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scheduled_tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  prompt TEXT NOT NULL,
  schedule_type TEXT NOT NULL CHECK(schedule_type IN ('interval','cron')),
  schedule TEXT NOT NULL,
  workspace TEXT NOT NULL DEFAULT '.',
  thread_id TEXT,
  enabled INTEGER NOT NULL DEFAULT 1,
  last_run_at TEXT,
  last_status TEXT,
  last_error TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    async def connect(self) -> aiosqlite.Connection:
        db = await aiosqlite.connect(self.path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys=ON")
        return db

    async def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = await self.connect()
        try:
            await db.executescript(SCHEMA)
            columns = {
                row[1]
                for row in await (await db.execute("PRAGMA table_info(projects)")).fetchall()
            }
            if "workspace" not in columns:
                await db.execute(
                    "ALTER TABLE projects ADD COLUMN workspace TEXT NOT NULL DEFAULT '.'"
                )
            await db.commit()
        finally:
            await db.close()

    async def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        db = await self.connect()
        try:
            cursor = await db.execute(sql, params)
            return [dict(row) for row in await cursor.fetchall()]
        finally:
            await db.close()

    async def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        rows = await self.fetchall(sql, params)
        return rows[0] if rows else None

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        db = await self.connect()
        try:
            cursor = await db.execute(sql, params)
            await db.commit()
            return int(cursor.lastrowid or 0)
        finally:
            await db.close()

    async def projects(self) -> list[dict[str, Any]]:
        return await self.fetchall("SELECT * FROM projects ORDER BY name COLLATE NOCASE")

    async def create_project(self, data: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        project_id = await self.execute(
            """INSERT INTO projects(name,description,color,workspace,created_at,updated_at)
               VALUES(?,?,?,?,?,?)""",
            (
                data["name"], data.get("description", ""), data.get("color"),
                data.get("workspace", "."), now, now,
            ),
        )
        return (await self.fetchone("SELECT * FROM projects WHERE id=?", (project_id,))) or {}

    async def update_project(self, project_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        current = await self.fetchone("SELECT * FROM projects WHERE id=?", (project_id,))
        if not current:
            return None
        for key in ("name", "description", "color", "workspace"):
            if key in data and data[key] is not None:
                current[key] = data[key]
        await self.execute(
            """UPDATE projects SET name=?,description=?,color=?,workspace=?,updated_at=?
               WHERE id=?""",
            (
                current["name"], current["description"], current["color"],
                current["workspace"], utc_now(), project_id,
            ),
        )
        return await self.fetchone("SELECT * FROM projects WHERE id=?", (project_id,))

    async def set_chat_metadata(
        self, thread_id: str, project_id: int | None, pinned: bool
    ) -> dict[str, Any]:
        await self.execute(
            """INSERT INTO chat_metadata(thread_id,project_id,pinned,updated_at) VALUES(?,?,?,?)
               ON CONFLICT(thread_id) DO UPDATE SET project_id=excluded.project_id,
               pinned=excluded.pinned,updated_at=excluded.updated_at""",
            (thread_id, project_id, int(pinned), utc_now()),
        )
        return (await self.fetchone("SELECT * FROM chat_metadata WHERE thread_id=?", (thread_id,))) or {}

    async def all_chat_metadata(self) -> dict[str, dict[str, Any]]:
        return {row["thread_id"]: row for row in await self.fetchall("SELECT * FROM chat_metadata")}

    async def settings(self) -> dict[str, Any]:
        rows = await self.fetchall("SELECT key,value_json FROM settings")
        return {row["key"]: json.loads(row["value_json"]) for row in rows}

    async def set_setting(self, key: str, value: Any) -> None:
        await self.execute(
            """INSERT INTO settings(key,value_json,updated_at) VALUES(?,?,?)
               ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json,updated_at=excluded.updated_at""",
            (key, json.dumps(value), utc_now()),
        )

    async def tasks(self) -> list[dict[str, Any]]:
        return await self.fetchall("SELECT * FROM scheduled_tasks ORDER BY id DESC")

    async def task(self, task_id: int) -> dict[str, Any] | None:
        return await self.fetchone("SELECT * FROM scheduled_tasks WHERE id=?", (task_id,))

    async def create_task(self, data: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        task_id = await self.execute(
            """INSERT INTO scheduled_tasks
               (name,prompt,schedule_type,schedule,workspace,thread_id,enabled,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                data["name"], data["prompt"], data["schedule_type"], data["schedule"],
                data.get("workspace", "."), data.get("thread_id"), int(data.get("enabled", True)),
                now, now,
            ),
        )
        return (await self.task(task_id)) or {}

    async def update_task(self, task_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        current = await self.task(task_id)
        if not current:
            return None
        keys = ("name", "prompt", "schedule_type", "schedule", "workspace", "thread_id", "enabled")
        for key in keys:
            if key in data and data[key] is not None:
                current[key] = int(data[key]) if key == "enabled" else data[key]
        await self.execute(
            """UPDATE scheduled_tasks SET name=?,prompt=?,schedule_type=?,schedule=?,workspace=?,
               thread_id=?,enabled=?,updated_at=? WHERE id=?""",
            tuple(current[k] for k in keys) + (utc_now(), task_id),
        )
        return await self.task(task_id)
