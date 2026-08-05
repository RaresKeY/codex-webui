from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pytest

from app.scheduler import TaskScheduler
from app.workspace import Workspace


class FakeDatabase:
    def __init__(self, task: dict[str, Any]) -> None:
        self.task_data = task
        self.executions: list[tuple[str, tuple[Any, ...]]] = []

    async def task(self, task_id: int) -> dict[str, Any] | None:
        return self.task_data if task_id == self.task_data["id"] else None

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        self.executions.append((sql, params))
        return 0


class CompletingCodex:
    def __init__(self, complete: bool = True) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.events: asyncio.Queue[dict[str, Any]] | None = None
        self.complete = complete

    @asynccontextmanager
    async def subscribe(self):
        self.events = asyncio.Queue()
        yield self.events

    async def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((method, params))
        if method == "turn/start":
            if self.complete:
                assert self.events
                self.events.put_nowait(
                    {
                        "method": "turn/completed",
                        "params": {
                            "threadId": params["threadId"],
                            "turn": {"id": "turn-1", "status": "completed"},
                        },
                    }
                )
            return {"turn": {"id": "turn-1"}}
        return {}


def task_record() -> dict[str, Any]:
    return {
        "id": 1, "name": "Task", "prompt": "Do it", "schedule_type": "interval",
        "schedule": "60", "workspace": "project", "thread_id": "thread-1", "enabled": 1,
    }


@pytest.mark.asyncio
async def test_resume_uses_validated_cwd_and_waits_for_terminal_turn(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    (root / "project").mkdir(parents=True)
    db = FakeDatabase(task_record())
    codex = CompletingCodex()
    scheduler = TaskScheduler(db, codex, Workspace(root, 1024))
    assert await scheduler.run_task(1) is True
    assert codex.calls[0] == (
        "thread/resume", {"threadId": "thread-1", "cwd": str(root / "project")}
    )
    assert any(params[0] == "completed" for _, params in db.executions if params)


@pytest.mark.asyncio
async def test_manual_runs_share_lease_and_are_cancelled_on_stop(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    (root / "project").mkdir(parents=True)
    db = FakeDatabase(task_record())
    scheduler = TaskScheduler(db, CompletingCodex(complete=False), Workspace(root, 1024))
    assert scheduler.launch_task(1) is True
    assert scheduler.launch_task(1) is False
    await asyncio.sleep(0)
    await scheduler.stop()
    assert scheduler._running_task_ids == set()
    assert scheduler._active_tasks == set()

