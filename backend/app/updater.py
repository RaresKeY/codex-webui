from __future__ import annotations

import asyncio
import shlex
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class Updater:
    def __init__(self, command: str | None, cwd: Path) -> None:
        self.command = command
        self.cwd = cwd
        self.state: dict[str, Any] = {
            "configured": bool(command), "running": False, "last_started_at": None,
            "last_finished_at": None, "returncode": None, "output": None,
        }
        self._task: asyncio.Task[None] | None = None

    def status(self) -> dict[str, Any]:
        return dict(self.state)

    def request(self) -> dict[str, Any]:
        if not self.command:
            raise ValueError("No update command is configured")
        if self._task and not self._task.done():
            raise RuntimeError("An update is already running")
        self._task = asyncio.create_task(self._run(), name="webui-update")
        return self.status() | {"accepted": True}

    async def _run(self) -> None:
        self.state.update(
            running=True,
            last_started_at=datetime.now(timezone.utc).isoformat(),
            last_finished_at=None,
            returncode=None,
            output=None,
        )
        try:
            process = await asyncio.create_subprocess_exec(
                *shlex.split(self.command or ""), cwd=self.cwd,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            )
            output, _ = await process.communicate()
            self.state["returncode"] = process.returncode
            self.state["output"] = output.decode(errors="replace")[-20000:]
        except Exception as exc:
            self.state["returncode"] = -1
            self.state["output"] = str(exc)
        finally:
            self.state["running"] = False
            self.state["last_finished_at"] = datetime.now(timezone.utc).isoformat()

