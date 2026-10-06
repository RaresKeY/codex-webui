from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, PropertyMock

import pytest
from fastapi.testclient import TestClient

from app.browser_service import BrowserAction, BrowserService, PublicBrowser, Session
from app.codex_client import CodexAppServerClient
from app.main import event_is_for_thread


@pytest.mark.parametrize('url', ['file:///etc/passwd', 'javascript:alert(1)', 'http://example.org', 'https://user:password@example.org', 'https://localhost', 'https://127.0.0.1'])
def test_browser_rejects_unsafe_navigation(url):
    assert not PublicBrowser([]).navigation_permitted(url)


def test_browser_navigation_and_scoping():
    assert PublicBrowser([]).navigation_permitted('https://example.org/path?q=hello')
    assert event_is_for_thread({'method': 'webui/browser', 'params': {'threadId': 'a'}}, 'a')
    assert not event_is_for_thread({'method': 'webui/browser', 'params': {'threadId': 'a'}}, 'b')


def test_browser_api_disabled_and_cross_site(client: TestClient):
    state = client.get('/api/threads/a/browser')
    assert state.status_code == 200
    assert state.headers['cache-control'] == 'no-store'
    assert state.json()['available'] is False
    assert client.post('/api/threads/a/browser', json={'action': 'open', 'url': 'https://example.org'}).status_code == 409
    assert client.post('/api/threads/a/browser', json={'action': 'open'}, headers={'origin': 'https://evil.example'}).status_code == 403
    assert client.post('/api/threads/a/browser', json={'action': 'evaluate', 'text': 'alert(1)'}).status_code == 422


class FixtureBrowser:
    def __init__(self):
        self.executed = []
        self.observations = 0
    def call(self, method, params):
        return {'data': 'frame'}
    def snapshot(self, config):
        self.observations += 1
        return {'version': 'v2', 'elements': [{'id': '0', 'destination': 'private', 'form_action': 'private', 'label': 'Next'}]}
    def evaluate(self, expression):
        return {'x': 64, 'y': 32}
    def execute(self, snapshot, action):
        self.executed.append(action)


@pytest.mark.asyncio
async def test_polling_preserves_observation_and_stale_actions_fail():
    publish = AsyncMock()
    service = BrowserService(True, publish)
    service.available = True
    browser = FixtureBrowser()
    session = Session(browser, snapshot={'version': 'v1'})
    service.sessions['a'] = session
    await service.refresh('a')
    assert session.snapshot['version'] == 'v1'
    assert browser.observations == 0
    with pytest.raises(ValueError, match='Stale'):
        await service.action('a', BrowserAction(action='click', target='0', version='old'))
    assert browser.executed == []
    publish.reset_mock()
    result = await service.action('a', BrowserAction(action='click', target='0', version='v1'))
    assert browser.executed[0]['target'] == '0'
    assert 'destination' not in result['elements'][0]
    assert 'form_action' not in result['elements'][0]
    signals = [call.args[0]['params'] for call in publish.await_args_list]
    assert [s['action'] for s in signals] == ['click', 'pointer', 'pointer', 'updated']
    assert signals[1]['cursor'] == {'x': 64, 'y': 32, 'click': False}
    assert signals[2]['cursor']['click'] is True
    assert all(s['threadId'] == 'a' and 'frame' not in s for s in signals)


@pytest.mark.asyncio
async def test_dynamic_tool_does_not_block_protocol_reader():
    client = CodexAppServerClient(['codex', 'app-server'])
    started, finish = asyncio.Event(), asyncio.Event()
    async def handle(params):
        started.set()
        await finish.wait()
        return {'success': True, 'contentItems': [{'type': 'inputText', 'text': 'observation'}]}
    client.browser_tool_handler = handle
    client._send = AsyncMock()
    await client.dispatch_message({'id': 'browser-1', 'method': 'item/tool/call', 'params': {'tool': 'browser', 'threadId': 'a', 'arguments': {'action': 'observe'}}})
    await started.wait()
    assert client.pending_server_requests() == []
    future = asyncio.get_running_loop().create_future()
    client._pending[8] = future
    await client.dispatch_message({'id': 8, 'result': {'ok': True}})
    assert await future == {'ok': True}
    finish.set()
    await asyncio.gather(*client._tool_tasks)
    assert client._send.await_args.args[0]['result']['success'] is True


def test_browser_tools_registered_only_on_verified_new_thread(client: TestClient, monkeypatch):
    client.app.state.browser.available = True
    codex = client.app.state.codex
    monkeypatch.setattr(type(codex), 'available', PropertyMock(return_value=True))
    client.app.state.chat.ensure_loaded = AsyncMock()
    codex.cli_version = 'codex-cli 0.160.1'
    codex.request = AsyncMock(return_value={'thread': {'id': 'a'}})
    assert client.post('/api/threads', json={}).status_code == 201
    params = codex.request.await_args.args[1]
    assert params['dynamicTools'][0]['type'] == 'function'
    assert params['dynamicTools'][0]['name'] == 'browser'
    assert client.post('/api/threads/a/resume', json={}).status_code == 200
    assert 'dynamicTools' not in codex.request.await_args.args[1]
    codex.cli_version = 'codex-cli 0.147.0'
    assert client.post('/api/threads', json={}).status_code == 201
    assert 'dynamicTools' not in codex.request.await_args.args[1]


@pytest.mark.asyncio
async def test_resolved_browser_request_cancels_pending_action():
    client = CodexAppServerClient(['codex', 'app-server'])
    started, cancelled = asyncio.Event(), asyncio.Event()
    async def handle(params):
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise
    client.browser_tool_handler = handle
    client._send = AsyncMock()
    await client.dispatch_message({'id': 7, 'method': 'item/tool/call', 'params': {'tool': 'browser', 'threadId': 'a'}})
    await started.wait()
    await client.dispatch_message({'method': 'serverRequest/resolved', 'params': {'requestId': 7}})
    await cancelled.wait()
    await asyncio.gather(*client._tool_tasks, return_exceptions=True)
    client._send.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancelled_launch_closes_browser_before_registration(monkeypatch):
    import threading
    import app.browser_service as module
    started, finish, closed = threading.Event(), threading.Event(), threading.Event()
    class StartupBrowser:
        def __init__(self, allowed): pass
        def navigation_permitted(self, url): return True
        def __enter__(self):
            started.set()
            finish.wait(timeout=5)
            return self
        def __exit__(self, *args): closed.set()
    monkeypatch.setattr(module, 'PublicBrowser', StartupBrowser)
    service = BrowserService(True, AsyncMock())
    service.available = True
    action = asyncio.create_task(service.action('a', BrowserAction(action='open', url='https://example.org')))
    await asyncio.to_thread(started.wait, 5)
    action.cancel()
    finish.set()
    with pytest.raises(asyncio.CancelledError):
        await action
    assert closed.is_set()
    assert service.sessions == {}

@pytest.mark.asyncio
async def test_human_browser_input_is_scoped_and_not_agent_tool():
    from app.browser_service import BrowserInput, BROWSER_TOOL
    from pydantic import ValidationError
    class InputBrowser(FixtureBrowser):
        def __init__(self):
            super().__init__()
            self.inputs = []
        def call(self, method, params):
            self.inputs.append((method, params))
            return super().call(method, params)
        def wait(self, seconds):
            pass
    service = BrowserService(True, AsyncMock())
    service.available = True
    browser = InputBrowser()
    service.sessions['a'] = Session(browser, snapshot={'version':'v1'})
    with pytest.raises(ValueError, match='this chat'):
        await service.user_input('b', BrowserInput(action='click', x=10, y=20))
    await service.user_input('a', BrowserInput(action='click', x=10, y=20))
    mouse = [params for method, params in browser.inputs if method == 'Input.dispatchMouseEvent']
    assert [item['type'] for item in mouse] == ['mousePressed', 'mouseReleased']
    assert all(item['x'] == 10 and item['y'] == 20 for item in mouse)
    with pytest.raises(ValueError, match='Stale'):
        await service.action('a', BrowserAction(action='click', target='0', version='v1'))
    await service.user_input('a', BrowserInput(action='text', text='human text'))
    assert ('Input.insertText', {'text':'human text'}) in browser.inputs
    await service.user_input('a', BrowserInput(action='key', key='Backspace'))
    assert any(method == 'Input.dispatchKeyEvent' and params['windowsVirtualKeyCode'] == 8 for method, params in browser.inputs)
    await service.user_input('a', BrowserInput(action='scroll', delta=-80))
    assert any(params.get('deltaY') == -80 for _, params in browser.inputs)
    assert 'x' not in BROWSER_TOOL['inputSchema']['properties']
    with pytest.raises(ValidationError):
        BrowserAction.model_validate({'action':'click','x':10,'y':20})
    for packet in [{'action':'click','x':1280}, {'action':'click','y':float('nan')}, {'action':'key','key':'F12'}, {'action':'scroll','delta':2000}]:
        with pytest.raises(ValidationError):
            BrowserInput.model_validate(packet)


def test_human_input_origin_and_schema(client: TestClient):
    assert client.post('/api/threads/a/browser/input', json={'action':'click','x':2,'y':3}, headers={'origin':'https://evil.example'}).status_code == 403
    assert client.post('/api/threads/a/browser/input', json={'action':'evaluate'}).status_code == 422
    assert client.post('/api/threads/a/browser/input', json={'action':'click','x':2,'y':3}).status_code == 409

@pytest.mark.asyncio
async def test_human_input_bridge_transport_is_separate():
    import httpx
    from pathlib import Path
    from app.browser_bridge import BrowserBridgeClient
    from app.browser_service import BrowserInput
    packets = []
    async def transport(request):
        import json
        packets.append((request.url.path, json.loads(request.content)))
        return httpx.Response(200, json={'available':True,'open':True,'revision':2})
    bridge = BrowserBridgeClient(Path('/not-used'), AsyncMock())
    await bridge.client.aclose()
    bridge.client = httpx.AsyncClient(transport=httpx.MockTransport(transport), base_url='http://browser')
    bridge.available = True
    try:
        state = await bridge.user_input('chat-a', BrowserInput(action='click', x=10, y=20))
        assert state['open'] and state['revision'] == 2
        assert packets[0][0] == '/threads/chat-a/input'
        assert packets[0][1]['x'] == 10
    finally:
        await bridge.client.aclose()
