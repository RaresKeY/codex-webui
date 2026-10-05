from unittest.mock import AsyncMock, PropertyMock
import asyncio

import pytest

from app.codex_client import CodexTimeout


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


@pytest.mark.asyncio
async def test_idle_websocket_disconnect_releases_the_native_subscription(client):
    disconnected = asyncio.Event()
    class Socket:
        headers = {"origin": "http://testserver", "host": "testserver"}
        accept = AsyncMock()
        send_json = AsyncMock()
        async def receive(self):
            await disconnected.wait()
            return {"type": "websocket.disconnect"}
    endpoint = next(route.endpoint for route in client.app.routes if getattr(route, "path", "") == "/ws/conversations/{thread_id}")
    task = asyncio.create_task(endpoint(Socket(), "one"))
    for _ in range(10):
        await asyncio.sleep(0)
        if client.app.state.codex._subscribers: break
    assert len(client.app.state.codex._subscribers) == 1
    disconnected.set()
    await asyncio.wait_for(task, timeout=.2)
    assert client.app.state.codex._subscribers == set()
