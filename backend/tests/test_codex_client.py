from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock

import pytest

from app.codex_client import CodexAppServerClient, CodexRPCError, CodexUnavailable


@pytest.mark.asyncio
async def test_dispatch_correlates_response() -> None:
    client = CodexAppServerClient(["codex", "app-server"])
    future = asyncio.get_running_loop().create_future()
    client._pending[7] = future
    await client.dispatch_message({"id": 7, "result": {"ok": True}})
    assert await future == {"ok": True}


@pytest.mark.asyncio
async def test_dispatch_correlates_rpc_error() -> None:
    client = CodexAppServerClient(["codex", "app-server"])
    future = asyncio.get_running_loop().create_future()
    client._pending[8] = future
    await client.dispatch_message({"id": 8, "error": {"code": -1, "message": "bad"}})
    with pytest.raises(CodexRPCError):
        await future


@pytest.mark.asyncio
async def test_server_request_is_published_and_stored() -> None:
    client = CodexAppServerClient(["codex", "app-server"])
    async with client.subscribe() as queue:
        message = {"id": 21, "method": "item/commandExecution/requestApproval", "params": {"command": "x"}}
        await client.dispatch_message(message)
        assert await queue.get() == message
    assert client.pending_server_requests()[0]["id"] == 21
    assert client.pending_server_requests()[0]["ui_supported"] is True


@pytest.mark.asyncio
async def test_unsupported_server_request_can_be_rejected() -> None:
    client = CodexAppServerClient(["codex", "app-server"])
    sent: list[dict[str, object]] = []

    async def capture(payload: dict[str, object]) -> None:
        sent.append(payload)

    client._send = capture  # type: ignore[method-assign]
    await client.dispatch_message(
        {"id": "tool-9", "method": "item/tool/call", "params": {"threadId": "t"}}
    )
    await client.reject_server_request("tool-9")

    assert sent == [
        {
            "id": "tool-9",
            "error": {
                "code": -32601,
                "message": "This App Server request is not supported by Codex WebUI",
            },
        }
    ]
    assert client.pending_server_requests() == []


@pytest.mark.asyncio
async def test_resolved_notification_and_stop_clear_pending_requests() -> None:
    client = CodexAppServerClient(["codex", "app-server"])
    await client.dispatch_message(
        {"id": 21, "method": "item/commandExecution/requestApproval", "params": {}}
    )
    await client.dispatch_message(
        {"method": "serverRequest/resolved", "params": {"requestId": 21}}
    )
    assert client.pending_server_requests() == []
    await client.dispatch_message(
        {"id": 22, "method": "auth/token/refresh", "params": {"reason": "expired"}}
    )
    assert client.pending_server_requests()[0]["ui_supported"] is False
    async with client.subscribe() as queue:
        await client.stop()
        cleared = await queue.get()
    assert cleared["method"] == "webui/serverRequestResolved"
    assert cleared["params"] == {"id": 22, "reason": "stopped", "cancelled": True}
    assert client.pending_server_requests() == []


@pytest.mark.asyncio
async def test_failed_server_response_remains_retryable() -> None:
    client = CodexAppServerClient(["codex", "app-server"])
    await client.dispatch_message(
        {"id": 23, "method": "item/fileChange/requestApproval", "params": {}}
    )
    client._send = AsyncMock(side_effect=CodexUnavailable("pipe closed"))
    with pytest.raises(CodexUnavailable):
        await client.respond_to_server_request("23", {"decision": "decline"})
    assert client.pending_server_requests()[0]["id"] == 23


@pytest.mark.asyncio
async def test_current_time_request_is_answered_automatically() -> None:
    client = CodexAppServerClient(["codex", "app-server"])
    client._send = AsyncMock()
    await client.dispatch_message(
        {"id": 24, "method": "currentTime/read", "params": {"threadId": "thread-1"}}
    )
    payload = client._send.await_args.args[0]
    assert payload["id"] == 24
    assert isinstance(payload["result"]["currentTimeAt"], int)
    assert client.pending_server_requests() == []


@pytest.mark.asyncio
async def test_subprocess_line_limit_fails_cleanly() -> None:
    script = (
        "import sys,time;"
        "sys.stdout.write('x'*70000+'\\n');sys.stdout.flush();time.sleep(5)"
    )
    client = CodexAppServerClient(
        [sys.executable, "-u", "-c", script], line_limit=64 * 1024
    )
    assert await asyncio.wait_for(client.start(), timeout=5) is False
    assert client.last_error and "exceeded 65536 byte limit" in client.last_error
    assert not client.available
