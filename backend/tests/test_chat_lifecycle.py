import asyncio
from unittest.mock import AsyncMock, PropertyMock

import pytest


def native(client, monkeypatch, *, status='idle', result=None):
    codex = client.app.state.codex
    monkeypatch.setattr(type(codex), 'available', PropertyMock(return_value=True))
    async def request(method, params):
        if method == 'thread/read':
            return {'thread': {'id': params['threadId'], 'status': {'type': status}}}
        if method == 'thread/unarchive':
            return result if result is not None else {'thread': {'id': params['threadId'], 'status': {'type': 'idle'}}}
        return result if result is not None else {}
    mock = AsyncMock(side_effect=request)
    monkeypatch.setattr(codex, 'request', mock)
    monkeypatch.setattr(client.app.state.router, 'choose', AsyncMock())
    return mock


@pytest.mark.parametrize('action,method,code', [('archive', 'thread/archive', 200), ('delete', 'thread/delete', 204), ('unarchive', 'thread/unarchive', 200)])
def test_lifecycle_uses_native_ack_and_never_routes_or_executes(client, monkeypatch, action, method, code):
    mock = native(client, monkeypatch)
    response = client.delete('/api/threads/one') if action == 'delete' else client.post('/api/threads/one/' + action)
    assert response.status_code == code
    assert [call.args[0] for call in mock.await_args_list] == ['thread/read', method]
    assert mock.await_args_list[-1].args[1] == {'threadId': 'one'}
    client.app.state.router.choose.assert_not_awaited()


@pytest.mark.parametrize('action', ['archive', 'delete', 'unarchive'])
def test_lifecycle_rejects_active_turns_and_pending_submissions(client, monkeypatch, action):
    mock = native(client, monkeypatch, status='active')
    invoke = lambda: client.delete('/api/threads/one') if action == 'delete' else client.post('/api/threads/one/' + action)
    assert invoke().status_code == 409
    assert mock.await_count == 1
    mock.reset_mock()
    client.app.state.chat._sending.add('one')
    try:
        assert invoke().status_code == 409
        mock.assert_not_awaited()
    finally:
        client.app.state.chat._sending.discard('one')


@pytest.mark.parametrize('action', ['archive', 'delete', 'unarchive'])
def test_lifecycle_rejects_unconfirmed_native_result(client, monkeypatch, action):
    native(client, monkeypatch, result={'unexpected': True})
    response = client.delete('/api/threads/one') if action == 'delete' else client.post('/api/threads/one/' + action)
    assert response.status_code == 502


def test_archive_restore_keep_selection_but_delete_cleans_only_target_state(client, monkeypatch):
    native(client, monkeypatch)
    db = client.app.state.db
    async def seed():
        await db.set_chat_metadata('one', None, True)
        await db.record_turn_selection('one', 't1', 'gpt-6-luna', 'low')
        await db.record_turn_selection('other', 't1', 'gpt-6.1-sol', 'high')
        await db.set_setting('chat-permissions:one', 'yolo')
        await db.set_setting('chat-execution:one', {'model':'auto', 'effort':'medium'})
        await db.set_setting('new-chat-permissions', 'yolo')
    asyncio.run(seed())
    assert client.post('/api/threads/one/archive').status_code == 200
    restored = client.post('/api/threads/one/unarchive').json()['thread']['webui']
    assert restored['pinned'] == 1 and restored['last_turn_model'] == 'gpt-6-luna'
    assert client.delete('/api/threads/one').status_code == 204
    async def verify():
        assert await db.turn_selections('one') == {}
        assert 'one' not in await db.all_chat_metadata()
        assert await db.get_setting('chat-permissions:one') is None
        assert await db.get_setting('chat-execution:one') is None
        assert await db.get_setting('new-chat-permissions') == 'yolo'
        assert await db.turn_selections('other')
    asyncio.run(verify())


def test_project_delete_unassigns_chats_without_deleting_workspace(client, workspace_root):
    project = client.post('/api/projects', json={'name': 'Temporary group', 'workspace': '.'}).json()
    assert client.patch('/api/threads/one/metadata', json={'project_id': project['id'], 'pinned': True}).status_code == 200
    marker = workspace_root / 'keep.txt'; marker.write_text('Keep this workspace file')
    assert client.delete(f"/api/projects/{project['id']}").status_code == 204
    assert marker.read_text() == 'Keep this workspace file'
    async def verify():
        metadata = (await client.app.state.db.all_chat_metadata())['one']
        assert metadata['project_id'] is None and metadata['pinned'] == 1
    asyncio.run(verify())
    assert client.delete(f"/api/projects/{project['id']}").status_code == 404
