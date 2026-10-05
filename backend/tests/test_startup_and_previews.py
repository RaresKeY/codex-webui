from unittest.mock import AsyncMock, PropertyMock
import asyncio
from types import SimpleNamespace
import socket

import pytest
import uvicorn
from websockets.asyncio.client import connect
from fastapi.testclient import TestClient

from app.codex_client import CodexTimeout
from app.main import create_app


def test_bootstrap_shell_never_waits_for_native_metadata(client, monkeypatch):
    codex = client.app.state.codex
    monkeypatch.setattr(type(codex), "available", PropertyMock(return_value=True))
    request = AsyncMock(side_effect=AssertionError("Bootstrap must not issue RPCs"))
    monkeypatch.setattr(codex, "request", request)
    response = client.get("/api/bootstrap")
    assert response.status_code == 200
    body = response.json()
    assert body["threads"]["data"] == [] and body["models"]["data"] == []
    assert body["health"]["codex_available"] is True
    request.assert_not_awaited()


def test_metadata_timeout_is_bounded_and_explicit(client, monkeypatch):
    codex = client.app.state.codex
    monkeypatch.setattr(type(codex), "available", PropertyMock(return_value=True))
    request = AsyncMock(side_effect=CodexTimeout("private diagnostic"))
    monkeypatch.setattr(codex, "request", request)
    response = client.get("/api/threads")
    assert response.status_code == 504 and "private" not in response.text
    assert "before retrying" in response.json()["detail"]
    assert request.await_count == 1


def test_workspace_image_preview_checks_bytes_and_root(client):
    root = client.app.state.settings.workspace_root
    image = b"\x89PNG\r\n\x1a\nfixture"
    (root / "preview.png").write_bytes(image)
    response = client.get("/api/workspace/image", params={"path": "preview.png"})
    assert response.status_code == 200 and response.content == image
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "no-store"
    assert client.get("/api/workspace/image", params={"path": str(root / "preview.png")}).status_code == 200
    outside = root.parent / "outside.png"
    outside.write_bytes(image)
    (root / "escape.png").symlink_to(outside)
    assert client.get("/api/workspace/image", params={"path": "escape.png"}).status_code == 403
    assert client.get("/api/workspace/image", params={"path": "../outside.png"}).status_code == 403
    assert client.get("/api/workspace/image", params={"path": "missing.png"}).status_code == 404
    (root / "fake.png").write_text("<svg onload='evil' />")
    assert client.get("/api/workspace/image", params={"path": "fake.png"}).status_code == 415


def test_workspace_image_preview_is_bounded(client):
    settings = client.app.state.settings
    settings.max_image_bytes = 16
    (settings.workspace_root / "big.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 9)
    assert client.get("/api/workspace/image", params={"path": "big.png"}).status_code == 413


def test_workspace_routes_protect_jev_keys_and_codex_state(settings, monkeypatch):
    root = settings.workspace_root
    key = root / ".env"
    key.write_text("JEV_API=synthetic-fixture")
    source = root / "jev-pipelines" / ".env"
    source.parent.mkdir()
    source.write_text("JEV_API=synthetic-mount-source")
    state = root / ".codex"
    state.mkdir()
    (state / "auth.json").write_text('{"fixture":true}')
    state_source = root / "host-codex-state"
    state_source.mkdir()
    (state_source / "auth.json").write_text('{"fixture":true}')
    settings.jev_key_file, settings.jev_key_source_file = key, source
    settings.codex_state_source_dir = state_source
    monkeypatch.setenv("CODEX_HOME", str(state))
    with TestClient(create_app(settings)) as client:
        for path in (".env", "jev-pipelines/.env", ".codex/auth.json", "host-codex-state/auth.json"):
            assert client.get("/api/workspace/file", params={"path": path}).status_code == 403
            assert client.put("/api/workspace/file", params={"path": path}, json={"content": "overwrite"}).status_code == 403
            assert client.get("/api/workspace/image", params={"path": path}).status_code == 403
        tree = client.get("/api/workspace/tree").json()
        assert all(entry["name"] not in (".codex", ".env", "host-codex-state") for entry in tree["children"])
        assert tree["children"][0]["children"] == []
    assert source.read_text() == "JEV_API=synthetic-mount-source"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/api/events", "/api/activity", "/ws/conversations/{thread_id}"])
async def test_idle_websocket_disconnect_releases_the_native_subscription(client, path):
    disconnected = asyncio.Event()
    class Socket:
        url = SimpleNamespace(path=path)
        headers = {"origin": "http://testserver", "host": "testserver"}
        accept = AsyncMock()
        send_json = AsyncMock()
        async def receive(self):
            await disconnected.wait()
            return {"type": "websocket.disconnect"}
    endpoint = next(route.endpoint for route in client.app.routes if getattr(route, "path", "") == path)
    task = asyncio.create_task(endpoint(Socket(), "one") if "thread_id" in path else endpoint(Socket()))
    for _ in range(10):
        await asyncio.sleep(0)
        if client.app.state.codex._subscribers: break
    assert len(client.app.state.codex._subscribers) == 1
    disconnected.set()
    await asyncio.wait_for(task, timeout=.2)
    assert client.app.state.codex._subscribers == set()


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/api/events", "/api/activity", "/ws/conversations/one"])
async def test_real_idle_websocket_disconnect_allows_clean_shutdown(settings, path):
    settings.allowed_hosts = ["127.0.0.1"]
    app = create_app(settings)
    server = uvicorn.Server(uvicorn.Config(app, log_level="critical", access_log=False, timeout_graceful_shutdown=1))
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        task = asyncio.create_task(server.serve(sockets=[listener]))
        try:
            async with asyncio.timeout(2):
                while not server.started:
                    if task.done(): await task
                    await asyncio.sleep(.01)
            async with connect(f"ws://127.0.0.1:{port}{path}", origin="http://testserver") as websocket:
                await asyncio.wait_for(websocket.recv(), timeout=1)
            async with asyncio.timeout(.5):
                while app.state.codex._subscribers:
                    await asyncio.sleep(.01)
            assert app.state.codex._subscribers == set()
        finally:
            server.should_exit = True
            await asyncio.wait_for(task, timeout=3)
        assert not server.server_state.tasks


@pytest.mark.asyncio
async def test_activity_feed_omits_transcript_payloads(client):
    disconnected = asyncio.Event()
    class Socket:
        url = SimpleNamespace(path="/api/activity")
        headers = {"origin": "http://testserver", "host": "testserver"}
        accept = AsyncMock()
        send_json = AsyncMock()
        async def receive(self):
            await disconnected.wait()
            return {"type": "websocket.disconnect"}
    socket = Socket()
    endpoint = next(route.endpoint for route in client.app.routes if getattr(route, "path", "") == "/api/activity")
    task = asyncio.create_task(endpoint(socket))
    for _ in range(20):
        await asyncio.sleep(0)
        if client.app.state.codex._subscribers: break
    queue = next(iter(client.app.state.codex._subscribers))
    await queue.put({"method": "item/agentMessage/delta", "params": {"threadId": "one", "delta": "synthetic-private-text"}})
    await queue.put({"method": "turn/started", "params": {"threadId": "one", "turn": {"id": "turn-one"}}})
    for _ in range(20):
        await asyncio.sleep(0)
        if socket.send_json.call_count >= 2: break
    methods = [call.args[0]["method"] for call in socket.send_json.call_args_list]
    assert "turn/started" in methods
    assert "item/agentMessage/delta" not in methods
    disconnected.set()
    await asyncio.wait_for(task, timeout=.2)

def test_thread_list_exposes_recorded_last_turn_instead_of_native_default(client, monkeypatch):
    import asyncio
    from unittest.mock import AsyncMock, PropertyMock
    monkeypatch.setattr(type(client.app.state.codex), "available", PropertyMock(return_value=True))
    db = client.app.state.db
    asyncio.run(db.record_turn_selection("selected", "first", "gpt-6.1-sol", "high"))
    asyncio.run(db.record_turn_selection("selected", "second", "gpt-6-luna", "low"))
    monkeypatch.setattr(client.app.state.codex, "request", AsyncMock(return_value={"data": [{"id": "selected", "model": "gpt-6.1-sol"}, {"id": "empty"}]}))
    result = client.get("/api/threads").json()["data"]
    assert result[0]["webui"]["last_turn_model"] == "gpt-6-luna"
    assert result[0]["webui"]["last_turn_effort"] == "low"
    assert result[0]["webui"]["project_id"] is None
    assert "last_turn_model" not in result[1]["webui"]
