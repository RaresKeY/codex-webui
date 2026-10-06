import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.browser_bridge import BrowserBridgeClient, create_bridge_app
from app.browser_service import BrowserAction


def test_bridge_schema_and_frame_projection():
    app = create_bridge_app()
    app.state.browser.refresh = AsyncMock(return_value={'frame': 'bounded-frame', 'threadId': 'a'})
    with TestClient(app) as client:
        assert client.get('/health').status_code == 200
        assert client.post('/threads/a', json={'action': 'evaluate', 'text': 'secret'}).status_code == 422
        assert client.get('/threads/a').json()['frame'] == 'bounded-frame'


@pytest.mark.asyncio
async def test_proxy_does_not_retry_failed_action(tmp_path):
    calls = []
    def handle(request):
        calls.append(request.url.path)
        if request.method == 'GET':
            return httpx.Response(200, json={'frame': 'bounded-frame'})
        return httpx.Response(409, json={'detail': 'stale'})
    proxy = BrowserBridgeClient(tmp_path / 'socket', AsyncMock())
    await proxy.client.aclose()
    proxy.client = httpx.AsyncClient(transport=httpx.MockTransport(handle), base_url='http://browser')
    proxy.available = True
    await proxy.refresh('a')
    with pytest.raises(httpx.HTTPStatusError):
        await proxy.action('a', BrowserAction(action='observe'))
    assert calls == ['/threads/a', '/threads/a']
    assert proxy.state('a')['frame'] == 'bounded-frame'
    await proxy.client.aclose()


@pytest.mark.asyncio
async def test_bridge_disconnect_cancels_action():
    app = create_bridge_app()
    cancelled = asyncio.Event()
    async def operation(*args):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()
    app.state.browser.action = operation
    endpoint = next(route.endpoint for route in app.routes if getattr(route, 'path', '') == '/threads/{thread_id}' and 'POST' in getattr(route, 'methods', set()))
    request = type('Disconnected', (), {'is_disconnected': AsyncMock(return_value=True)})()
    with pytest.raises(Exception):
        await asyncio.wait_for(endpoint('a', BrowserAction(action='observe'), request), 1)
    assert cancelled.is_set()


@pytest.mark.asyncio
async def test_clean_event_stream_eof_backs_off(tmp_path, monkeypatch):
    calls = []
    async def handle(request):
        calls.append(request.url.path)
        return httpx.Response(200, text='{"ready":true}\n')
    proxy = BrowserBridgeClient(tmp_path / 'socket', AsyncMock())
    await proxy.client.aclose()
    proxy.client = httpx.AsyncClient(transport=httpx.MockTransport(handle), base_url='http://browser')
    delays = []
    async def stop_after_delay(seconds):
        delays.append(seconds)
        raise asyncio.CancelledError
    monkeypatch.setattr('app.browser_bridge.asyncio.sleep', stop_after_delay)
    try:
        with pytest.raises(asyncio.CancelledError):
            await proxy._events()
        assert calls == ['/events']
        assert delays == [1]
        assert proxy.ready.is_set()
    finally:
        await proxy.client.aclose()
