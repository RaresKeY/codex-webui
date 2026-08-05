from __future__ import annotations

import asyncio
import logging
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .codex_client import CodexAppServerClient
from .database import Database
from .models import utc_now
from .workspace import Workspace

logger = logging.getLogger(__name__)


class TaskScheduler:
    def __init__(
        self,
        db: Database,
        codex: CodexAppServerClient,
        workspace: Workspace,
        approval_policy: str = "on-request",
        sandbox: str = "workspace-write",
    ) -> None:
        self.db = db
        self.codex = codex
        self.workspace = workspace
        self.approval_policy = approval_policy
        self.sandbox = sandbox
        self.scheduler = AsyncIOScheduler(timezone="UTC")
        self._running_task_ids: set[int] = set()
        self._active_tasks: set[asyncio.Task[Any]] = set()

    async def start(self) -> None:
        self.scheduler.start()
        for task in await self.db.tasks():
            if task["enabled"]:
                self.schedule(task)

    async def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        current = asyncio.current_task()
        active = tuple(task for task in self._active_tasks if task is not current)
        for task in active:
            task.cancel()
        if active:
            await asyncio.gather(*active, return_exceptions=True)
        self._active_tasks.clear()
        self._running_task_ids.clear()

    def schedule(self, task: dict[str, Any]) -> None:
        trigger = self._trigger(task["schedule_type"], task["schedule"])
        self.scheduler.add_job(
            self.run_task,
            trigger=trigger,
            args=[task["id"]],
            id=f"task-{task['id']}",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

    def unschedule(self, task_id: int) -> None:
        job = self.scheduler.get_job(f"task-{task_id}")
        if job:
            job.remove()

    def refresh(self, task: dict[str, Any]) -> None:
        self.unschedule(task["id"])
        if task["enabled"]:
            self.schedule(task)

    @staticmethod
    def _trigger(schedule_type: str, schedule: str) -> Any:
        if schedule_type == "interval":
            seconds = int(schedule)
            if seconds < 10:
                raise ValueError("interval must be at least 10 seconds")
            return IntervalTrigger(seconds=seconds)
        return CronTrigger.from_crontab(schedule, timezone="UTC")

    def launch_task(self, task_id: int) -> bool:
        """Reserve and launch a manual run atomically from the event loop."""
        if task_id in self._running_task_ids:
            return False
        self._running_task_ids.add(task_id)
        task = asyncio.create_task(self._run_reserved(task_id, require_enabled=False))
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)
        return True

    async def run_task(self, task_id: int) -> bool:
        """Run a scheduled task unless a manual or scheduled run owns it."""
        if task_id in self._running_task_ids:
            return False
        self._running_task_ids.add(task_id)
        current = asyncio.current_task()
        if current:
            self._active_tasks.add(current)
        try:
            await self._run_reserved(task_id, require_enabled=True)
            return True
        finally:
            if current:
                self._active_tasks.discard(current)

    async def _run_reserved(self, task_id: int, require_enabled: bool) -> None:
        try:
            await self._execute_task(task_id, require_enabled=require_enabled)
        finally:
            self._running_task_ids.discard(task_id)

    async def _execute_task(self, task_id: int, require_enabled: bool) -> None:
        task = await self.db.task(task_id)
        if not task or (require_enabled and not task["enabled"]):
            return
        try:
            cwd = str(self.workspace.resolve(task["workspace"], must_exist=True))
            if task["thread_id"]:
                await self.codex.request(
                    "thread/resume", {"threadId": task["thread_id"], "cwd": cwd}
                )
                thread_id = task["thread_id"]
            else:
                result = await self.codex.request(
                    "thread/start",
                    {
                        "cwd": cwd,
                        "approvalPolicy": self.approval_policy,
                        "sandbox": self.sandbox,
                    },
                )
                thread = result.get("thread", result) if isinstance(result, dict) else {}
                thread_id = thread.get("id") or thread.get("threadId")
                if not thread_id:
                    raise RuntimeError("thread/start did not return a thread id")
            async with self.codex.subscribe() as events:
                turn_result = await self.codex.request(
                    "turn/start",
                    {"threadId": thread_id, "input": [{"type": "text", "text": task["prompt"]}]},
                )
                turn = turn_result.get("turn", turn_result) if isinstance(turn_result, dict) else {}
                turn_id = turn.get("id") or turn.get("turnId")
                if not turn_id:
                    raise RuntimeError("turn/start did not return a turn id")
                await self.db.execute(
                    "UPDATE scheduled_tasks SET last_run_at=?,last_status='running',last_error=NULL WHERE id=?",
                    (utc_now(), task_id),
                )
                terminal_turn = await self._wait_for_turn_completion(
                    events, str(thread_id), str(turn_id)
                )
            terminal_status = str(terminal_turn.get("status") or "completed")
            terminal_error = terminal_turn.get("error")
            await self.db.execute(
                "UPDATE scheduled_tasks SET last_status=?,last_error=? WHERE id=?",
                (
                    terminal_status,
                    str(terminal_error)[:2000] if terminal_error is not None else None,
                    task_id,
                ),
            )
        except Exception as exc:
            logger.exception("Scheduled task %s failed", task_id)
            await self.db.execute(
                "UPDATE scheduled_tasks SET last_run_at=?,last_status='error',last_error=? WHERE id=?",
                (utc_now(), str(exc)[:2000], task_id),
            )

    @staticmethod
    async def _wait_for_turn_completion(
        events: asyncio.Queue[dict[str, Any]], thread_id: str, turn_id: str
    ) -> dict[str, Any]:
        while True:
            message = await events.get()
            method = message.get("method")
            params = message.get("params", {})
            if method == "webui/disconnected":
                raise RuntimeError("Codex disconnected during scheduled turn")
            if method != "turn/completed" or not isinstance(params, dict):
                continue
            event_thread = params.get("threadId")
            turn = params.get("turn", {})
            event_turn = turn.get("id") if isinstance(turn, dict) else params.get("turnId")
            if str(event_thread) == thread_id and str(event_turn) == turn_id:
                return turn if isinstance(turn, dict) else {"id": event_turn}
