"""Narrow Unix-socket browser transport; never exposes commands, files or CDP."""
from __future__ import annotations

import asyncio
import contextlib
import json
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

from .browser_service import BrowserAction, BrowserService


class BrowserBridgeClient(BrowserService):
    def __init__(self, socket: Path, publish):
        self.available = False
        self.agent_available = False
        self.publish = publish
        self.states = {}
        self.client = httpx.AsyncClient(transport=httpx.AsyncHTTPTransport(uds=str(socket)),
                                       base_url='http://browser', timeout=45)
        self.events_task = None
        self.ready = asyncio.Event()

    async def start(self):
        try:
            response = await self.client.get('/health')
            response.raise_for_status()
            self.available = response.json().get('available') is True
            if self.available:
                self.events_task = asyncio.create_task(self._events())
                await asyncio.wait_for(self.ready.wait(), 5)
        except (httpx.HTTPError, asyncio.TimeoutError):
            self.available = False

    async def _events(self):
        while True:
            try:
                async with self.client.stream('GET', '/events', timeout=None) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        event = json.loads(line)
                        if event.get('ready'):
                            self.ready.set()
                            continue
                        if event.get('method') != 'webui/browser':
                            continue
                        params = event.get('params', {})
                        thread = params.get('threadId')
                        if not isinstance(thread, str):
                            continue
                        params['agentAvailable'] = self.agent_available
                        cached = self.states.setdefault(thread, {})
                        # Bridge action state excludes frames; retain the last bounded frame.
                        cached.update(params)
                        await self.publish(event)
            except (httpx.HTTPError, ValueError):
                # Reconnect event transport only; never retry an action.
                await asyncio.sleep(1)

    def state(self, thread_id):
        return {**self.states.get(thread_id, {}), 'available': self.available,
                'agentAvailable': self.agent_available}

    async def refresh(self, thread_id):
        response = await self.client.get('/threads/' + quote(thread_id, safe=''))
        response.raise_for_status()
        self.states[thread_id] = response.json()
        return self.state(thread_id)

    async def action(self, thread_id, action):
        if not self.available:
            raise ValueError('Browser bridge unavailable')
        response = await self.client.post('/threads/' + quote(thread_id, safe=''), json=action.model_dump())
        response.raise_for_status()
        result = response.json()
        self.states[thread_id] = result['state']
        return result['observation']

    async def stop(self):
        if self.available:
            with contextlib.suppress(httpx.HTTPError):
                await self.client.post('/close-all')
        if self.events_task:
            self.events_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.events_task
        await self.client.aclose()


def create_bridge_app():
    subscribers = set()

    async def publish(event):
        for queue in tuple(subscribers):
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(event)

    browser = BrowserService(True, publish)

    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            await browser.stop()

    app = FastAPI(lifespan=lifespan)
    app.state.browser = browser

    @app.get('/health')
    async def health():
        return {'available': browser.available}

    @app.get('/events')
    async def events():
        async def stream():
            queue = asyncio.Queue(maxsize=128)
            subscribers.add(queue)
            try:
                yield '{"ready":true}\n'
                while True:
                    yield json.dumps(await queue.get()) + '\n'
            finally:
                subscribers.discard(queue)
        return StreamingResponse(stream(), media_type='application/x-ndjson')

    @app.get('/threads/{thread_id}')
    async def state(thread_id: str):
        try:
            return await browser.refresh(thread_id)
        except Exception:
            raise HTTPException(503, 'Browser frame unavailable') from None

    @app.post('/threads/{thread_id}')
    async def action(thread_id: str, body: BrowserAction, request: Request):
        operation = asyncio.create_task(browser.action(thread_id, body))
        async def disconnected():
            while not await request.is_disconnected():
                await asyncio.sleep(0.1)
        watcher = asyncio.create_task(disconnected())
        try:
            done, _ = await asyncio.wait({operation, watcher}, return_when=asyncio.FIRST_COMPLETED)
            if operation not in done:
                operation.cancel()
                await asyncio.gather(operation, return_exceptions=True)
                raise HTTPException(499, 'Browser client disconnected')
            result = await operation
            return {'observation': result, 'state': browser.state(thread_id)}
        except Exception:
            raise HTTPException(409, 'Browser action failed or observation stale') from None
        finally:
            operation.cancel()
            watcher.cancel()
            await asyncio.gather(operation, watcher, return_exceptions=True)

    @app.post('/close-all')
    async def close_all():
        await browser.stop()
        return {'closed': True}

    return app


app = create_bridge_app()
