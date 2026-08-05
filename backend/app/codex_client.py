from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class CodexUnavailable(RuntimeError):
    pass


class CodexRPCError(RuntimeError):
    def __init__(self, error: Any):
        super().__init__(str(error))
        self.error = error


@dataclass
class ServerRequest:
    id: int | str
    method: str
    params: Any
    received_at: str
    ui_supported: bool


UI_SERVER_REQUEST_METHODS = {
    "item/commandExecution/requestApproval",
    "item/fileChange/requestApproval",
    "item/permissions/requestApproval",
    "item/tool/requestUserInput",
    "mcpServer/elicitation/request",
}


class CodexAppServerClient:
    """Async JSONL client for `codex app-server`.

    JSON-RPC responses are correlated by id, notifications are broadcast to every
    websocket subscriber, and server-initiated requests are retained until the UI
    supplies a response. Unknown protocol fields are passed through unchanged so a
    newer Codex CLI can be used without a backend release.
    """

    def __init__(
        self,
        argv: list[str],
        enabled: bool = True,
        line_limit: int = 32 * 1024 * 1024,
    ) -> None:
        if line_limit < 1024:
            raise ValueError("line_limit must be at least 1024 bytes")
        self.argv = argv
        self.enabled = enabled
        self.line_limit = line_limit
        self.process: asyncio.subprocess.Process | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._stderr_task: asyncio.Task[None] | None = None
        self._pending: dict[int, asyncio.Future[Any]] = {}
        self._server_requests: dict[str, ServerRequest] = {}
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._write_lock = asyncio.Lock()
        self._next_id = 1
        self.last_error: str | None = None
        self.server_info: dict[str, Any] | None = None

    @property
    def available(self) -> bool:
        return bool(self.process and self.process.returncode is None)

    async def start(self) -> bool:
        if not self.enabled or not self.argv:
            self.last_error = "Codex app-server is disabled"
            return False
        if self.available:
            return True
        try:
            self.process = await asyncio.create_subprocess_exec(
                *self.argv,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=self.line_limit,
            )
            self._reader_task = asyncio.create_task(self._read_loop(), name="codex-stdout")
            self._stderr_task = asyncio.create_task(self._stderr_loop(), name="codex-stderr")
            self.server_info = await asyncio.wait_for(
                self.request(
                    "initialize",
                    {
                        "clientInfo": {
                            "name": "codex-webui",
                            "title": "Codex WebUI",
                            "version": "0.1.0",
                        }
                    },
                ),
                timeout=15,
            )
            await self.notify("initialized", {})
            self.last_error = None
            return True
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            logger.warning("Codex app-server unavailable: %s", self.last_error)
            await self.stop()
            return False

    async def stop(self) -> None:
        process, self.process = self.process, None
        if process and process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
        current = asyncio.current_task()
        for task in (self._reader_task, self._stderr_task):
            if task and task is not current:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        self._reader_task = self._stderr_task = None
        self._fail_pending(CodexUnavailable("Codex app-server stopped"))
        await self._clear_server_requests("stopped")

    async def request(self, method: str, params: Any | None = None) -> Any:
        if not self.available or not self.process or not self.process.stdin:
            raise CodexUnavailable(self.last_error or "Codex app-server is unavailable")
        request_id = self._next_id
        self._next_id += 1
        future = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        try:
            await self._send({"id": request_id, "method": method, "params": params or {}})
            return await future
        finally:
            self._pending.pop(request_id, None)

    async def notify(self, method: str, params: Any | None = None) -> None:
        await self._send({"method": method, "params": params or {}})

    async def respond_to_server_request(self, request_id: str, result: Any) -> None:
        request = self._server_requests.get(str(request_id))
        if request is None:
            raise KeyError(request_id)
        response_id: int | str = request.id
        await self._send({"id": response_id, "result": result})
        # Keep a request retryable if the write or drain fails. Remove it only
        # after the response has reached the subprocess pipe successfully.
        self._server_requests.pop(str(request_id), None)
        await self._publish(
            {"method": "webui/serverRequestResolved", "params": {"id": response_id}}
        )

    async def reject_server_request(
        self,
        request_id: str,
        message: str = "This App Server request is not supported by Codex WebUI",
    ) -> None:
        """Finish an unsupported JSON-RPC request with a protocol error."""
        request = self._server_requests.get(str(request_id))
        if request is None:
            raise KeyError(request_id)
        response_id: int | str = request.id
        await self._send(
            {
                "id": response_id,
                "error": {"code": -32601, "message": message},
            }
        )
        self._server_requests.pop(str(request_id), None)
        await self._publish(
            {
                "method": "webui/serverRequestResolved",
                "params": {"id": response_id, "rejected": True},
            }
        )

    def pending_server_requests(self) -> list[dict[str, Any]]:
        return [asdict(item) for item in self._server_requests.values()]

    @contextlib.asynccontextmanager
    async def subscribe(self, maxsize: int = 512) -> AsyncIterator[asyncio.Queue[dict[str, Any]]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=maxsize)
        self._subscribers.add(queue)
        try:
            yield queue
        finally:
            self._subscribers.discard(queue)

    async def _send(self, payload: dict[str, Any]) -> None:
        if not self.available or not self.process or not self.process.stdin:
            raise CodexUnavailable(self.last_error or "Codex app-server is unavailable")
        data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode() + b"\n"
        async with self._write_lock:
            self.process.stdin.write(data)
            await self.process.stdin.drain()

    async def _read_loop(self) -> None:
        process = self.process
        assert process and process.stdout
        try:
            while line := await process.stdout.readline():
                try:
                    message = json.loads(line)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    logger.debug("Ignoring non-JSON app-server stdout: %r", line[:300])
                    continue
                await self.dispatch_message(message)
            if process.returncode is None:
                await self._terminate_process(process)
                self.last_error = (
                    f"Codex app-server closed its protocol stream with status {process.returncode}"
                )
            else:
                self.last_error = f"Codex app-server exited with status {process.returncode}"
        except asyncio.CancelledError:
            raise
        except ValueError as exc:
            # asyncio translates LimitOverrunError from StreamReader.readline
            # into ValueError. Treat it as a fatal protocol violation instead of
            # leaving a live child with a permanently desynchronized stream.
            self.last_error = (
                f"App-server protocol line exceeded {self.line_limit} byte limit: {exc}"
            )
            logger.error("%s", self.last_error)
            await self._terminate_process(process)
        except Exception as exc:
            self.last_error = f"App-server read error: {exc}"
            logger.exception("Codex app-server read loop failed")
            await self._terminate_process(process)
        finally:
            self._fail_pending(CodexUnavailable(self.last_error or "Codex app-server closed"))
            await self._clear_server_requests("disconnected")
            await self._publish(
                {"method": "webui/disconnected", "params": {"error": self.last_error}}
            )

    async def dispatch_message(self, message: dict[str, Any]) -> None:
        """Dispatch one decoded message. Kept public for protocol tests."""
        method = message.get("method")
        if method == "serverRequest/resolved":
            params = message.get("params", {})
            if isinstance(params, dict):
                resolved_id = next(
                    (
                        params[key]
                        for key in ("requestId", "serverRequestId", "id")
                        if params.get(key) is not None
                    ),
                    None,
                )
                if resolved_id is not None:
                    removed = self._server_requests.pop(str(resolved_id), None)
                    if removed is not None:
                        await self._publish(
                            {
                                "method": "webui/serverRequestResolved",
                                "params": {"id": resolved_id, "reason": "server-resolved"},
                            }
                        )

        request_id = message.get("id")
        if request_id is not None and "method" not in message:
            future = self._pending.get(request_id)
            if future and not future.done():
                if "error" in message:
                    future.set_exception(CodexRPCError(message["error"]))
                else:
                    future.set_result(message.get("result"))
            return

        if request_id is not None and "method" in message:
            if method == "currentTime/read":
                await self._send(
                    {
                        "id": request_id,
                        "result": {
                            "currentTimeAt": int(datetime.now(timezone.utc).timestamp())
                        },
                    }
                )
                await self._publish(message)
                await self._publish(
                    {
                        "method": "webui/serverRequestResolved",
                        "params": {"id": request_id, "automatic": True},
                    }
                )
                return
            item = ServerRequest(
                id=request_id,
                method=str(message["method"]),
                params=message.get("params", {}),
                received_at=datetime.now(timezone.utc).isoformat(),
                ui_supported=str(message["method"]) in UI_SERVER_REQUEST_METHODS,
            )
            self._server_requests[str(request_id)] = item
        await self._publish(message)

    async def _publish(self, message: dict[str, Any]) -> None:
        for queue in tuple(self._subscribers):
            if queue.full():
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(message)

    async def _stderr_loop(self) -> None:
        process = self.process
        assert process and process.stderr
        try:
            # stderr is diagnostic, not framed protocol. Fixed-size reads avoid
            # applying JSONL line limits to a tool that emits a long log line.
            while chunk := await process.stderr.read(8192):
                # Drain without retaining or logging potentially sensitive paths,
                # commands, tokens, or model output contained in diagnostics.
                logger.debug("drained %d bytes from codex app-server stderr", len(chunk))
        except asyncio.CancelledError:
            raise

    @staticmethod
    async def _terminate_process(process: asyncio.subprocess.Process) -> None:
        if process.returncode is not None:
            return
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=2)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()

    def _fail_pending(self, exc: Exception) -> None:
        for future in tuple(self._pending.values()):
            if not future.done():
                future.set_exception(exc)

    async def _clear_server_requests(self, reason: str) -> None:
        outstanding = tuple(self._server_requests.values())
        self._server_requests.clear()
        for request in outstanding:
            await self._publish(
                {
                    "method": "webui/serverRequestResolved",
                    "params": {
                        "id": request.id,
                        "reason": reason,
                        "cancelled": True,
                    },
                }
            )
