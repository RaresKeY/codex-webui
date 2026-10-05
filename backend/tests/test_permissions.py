import asyncio

import pytest

from app.chat_service import MessageError
from app.codex_client import CodexRPCError
from app.database import Database
from test_routed_chat import ASK, setup


@pytest.mark.parametrize('mode,policy,reviewer,sandbox', [
    ('default', 'on-request', 'user', 'workspaceWrite'),
    ('full-auto', 'on-request', 'auto_review', 'dangerFullAccess'),
    ('yolo', 'never', 'user', 'dangerFullAccess'),
])
def test_acknowledged_permissions_are_thread_scoped_and_reapplied_before_the_exact_ask(client, monkeypatch, mode, policy, reviewer, sandbox):
    calls = setup(client, monkeypatch, loaded=False)
    assert client.get('/api/threads/one/permissions').json() == {'mode':'default'}
    response = client.patch('/api/threads/one/permissions', json={'mode':mode})
    assert response.status_code == 200
    assert response.json() == {'mode':mode, 'acknowledged':True}
    selected = calls[-1][1]
    assert selected['approvalPolicy'] == policy
    assert selected['approvalsReviewer'] == reviewer
    assert selected['sandboxPolicy']['type'] == sandbox
    assert [method for method, _ in calls] == ['thread/read', 'thread/loaded/list', 'thread/resume', 'thread/settings/update']
    assert client.get('/api/threads/one/permissions').json() == {'mode':mode}
    assert client.get('/api/threads/two/permissions').json() == {'mode':'default'}
    calls.clear()
    response = client.post('/api/threads/one/messages', json={'input':ASK})
    assert response.status_code == 201
    assert [method for method, _ in calls] == ['thread/read', 'jev', 'thread/loaded/list', 'thread/resume', 'thread/settings/update', 'turn/start']
    bound, started = calls[-2][1], calls[-1][1]
    for key in ('approvalPolicy', 'approvalsReviewer', 'sandboxPolicy'):
        assert bound[key] == selected[key] == started[key]
    assert started['input'] == [{'type':'text', 'text':ASK}]


@pytest.mark.parametrize('payload', [{'mode':'invalid'}, {'mode':'yolo','sandbox':'anything'}, {}])
def test_invalid_permission_changes_do_not_call_native_codex(client, monkeypatch, payload):
    calls = setup(client, monkeypatch)
    assert client.patch('/api/threads/one/permissions', json=payload).status_code == 422
    assert calls == []


def test_rejected_native_permissions_do_not_replace_the_saved_choice_or_leak_diagnostics(client, monkeypatch):
    setup(client, monkeypatch)
    assert client.patch('/api/threads/one/permissions', json={'mode':'full-auto'}).status_code == 200
    original = client.app.state.codex.request
    async def rejected(method, params):
        if method == 'thread/settings/update':
            raise CodexRPCError({'message':'private managed restriction'})
        return await original(method, params)
    monkeypatch.setattr(client.app.state.codex, 'request', rejected)
    response = client.patch('/api/threads/one/permissions', json={'mode':'yolo'})
    assert response.status_code == 502 and 'private' not in response.text
    assert client.get('/api/threads/one/permissions').json() == {'mode':'full-auto'}


def test_permission_metadata_cannot_substitute_for_native_acknowledgement(client, monkeypatch):
    setup(client, monkeypatch)
    original = client.app.state.codex.request
    async def unacknowledged(method, params):
        if method == 'thread/settings/update':
            return {'thread': {'id':'one'}}
        return await original(method, params)
    monkeypatch.setattr(client.app.state.codex, 'request', unacknowledged)
    response = client.patch('/api/threads/one/permissions', json={'mode':'yolo'})
    assert response.status_code == 502
    assert client.get('/api/threads/one/permissions').json() == {'mode':'default'}


def test_active_turn_cannot_change_permissions(client, monkeypatch):
    calls = setup(client, monkeypatch)
    client.app.state.codex.request.return_value = {'thread': {'id':'one', 'status':{'type':'active'}}}
    client.app.state.codex.request.side_effect = None
    assert client.patch('/api/threads/one/permissions', json={'mode':'yolo'}).status_code == 409
    assert calls == []
    assert client.app.state.codex.request.await_count == 1


@pytest.mark.asyncio
async def test_change_and_send_cannot_overlap_and_no_selection_is_saved_before_acknowledgement(client, monkeypatch):
    setup(client, monkeypatch)
    codex = client.app.state.codex
    original = codex.request
    binding = asyncio.Event()
    acknowledge = asyncio.Event()
    async def request(method, params):
        if method == 'thread/settings/update':
            binding.set()
            await acknowledge.wait()
        return await original(method, params)
    monkeypatch.setattr(codex, 'request', request)
    chat = client.app.state.chat
    changing = asyncio.create_task(chat.set_permissions('one', 'yolo'))
    await asyncio.wait_for(binding.wait(), 2)
    assert await chat.permission_mode('one') == 'default'
    with pytest.raises(MessageError, match='already being submitted'):
        await chat.set_permissions('one', 'full-auto')
    acknowledge.set()
    await asyncio.wait_for(changing, 2)
    assert await chat.permission_mode('one') == 'yolo'


@pytest.mark.asyncio
async def test_saved_selection_survives_database_reopening_and_corrupt_choices_fail_closed(client, monkeypatch):
    setup(client, monkeypatch)
    chat = client.app.state.chat
    await chat.set_permissions('one', 'yolo')
    reopened = Database(client.app.state.db.path)
    await reopened.initialize()
    assert await reopened.get_setting('chat-permissions:one') == 'yolo'
    await reopened.set_setting('chat-permissions:one', 'corrupt')
    with pytest.raises(MessageError, match='invalid'):
        await chat.permission_mode('one')
