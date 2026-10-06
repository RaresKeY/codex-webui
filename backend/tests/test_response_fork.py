import asyncio
from unittest.mock import AsyncMock, PropertyMock

import pytest


def setup_native(client, monkeypatch, workspace_root, *, status='completed', ack=None):
    codex = client.app.state.codex
    monkeypatch.setattr(type(codex), 'available', PropertyMock(return_value=True))
    codex.cli_version = 'codex-cli 0.160.1'
    async def request(method, params):
        if method == 'thread/read':
            return {'thread': {'id': 'source', 'cwd': str(workspace_root), 'turns': [{'id': 'early', 'status': status}, {'id': 'later', 'status': 'completed'}]}}
        return ack if ack is not None else {'thread': {'id': 'branch', 'cwd': str(workspace_root), 'turns': [{'id': 'early', 'status': status}]}}
    mock = AsyncMock(side_effect=request)
    monkeypatch.setattr(codex, 'request', mock)
    monkeypatch.setattr(client.app.state.router, 'choose', AsyncMock())
    return mock


def test_response_branch_uses_inclusive_turn_and_defers_goal_without_inference(client, monkeypatch, workspace_root):
    native = setup_native(client, monkeypatch, workspace_root)
    db = client.app.state.db
    async def seed():
        await db.record_turn_selection('source', 'early', 'gpt-6-luna', 'low')
        await db.record_turn_selection('source', 'later', 'gpt-6.1-sol', 'high')
        await db.set_setting('chat-permissions:source', 'yolo')
    asyncio.run(seed())
    response = client.post('/api/threads/source/fork', json={'turn_id': 'early'})
    assert response.status_code == 201
    assert response.json()['thread']['id'] == 'branch'
    assert response.json()['metadataSaved'] is True
    assert [call.args[0] for call in native.await_args_list] == ['thread/read', 'thread/fork']
    assert native.await_args_list[-1].args[1] == {'threadId': 'source', 'lastTurnId': 'early', 'deferGoalContinuation': True}
    client.app.state.router.choose.assert_not_awaited()
    async def verify():
        assert await db.turn_selections('branch') == {'early': {'model': 'gpt-6-luna', 'effort': 'low'}}
        assert len(await db.turn_selections('source')) == 2
        assert await db.get_setting('chat-permissions:branch') == 'yolo'
    asyncio.run(verify())


@pytest.mark.parametrize('body,code', [({'turn_id': 'missing'}, 404), ({'turn_id': ''}, 422), ({'turn_id': 'early', 'lastTurnId': 'later'}, 422)])
def test_branch_rejects_unknown_or_unbounded_parameters(client, monkeypatch, workspace_root, body, code):
    native = setup_native(client, monkeypatch, workspace_root)
    assert client.post('/api/threads/source/fork', json=body).status_code == code
    assert all(call.args[0] == 'thread/read' for call in native.await_args_list)


def test_branch_rejects_running_turn_and_unconfirmed_ack(client, monkeypatch, workspace_root):
    native = setup_native(client, monkeypatch, workspace_root, status='inProgress')
    assert client.post('/api/threads/source/fork', json={'turn_id': 'early'}).status_code == 409
    assert native.await_count == 1
    setup_native(client, monkeypatch, workspace_root, ack={'thread': {'id': 'source'}})
    assert client.post('/api/threads/source/fork', json={'turn_id': 'early'}).status_code == 502


def test_optional_metadata_failure_does_not_retry_or_reject_created_branch(client, monkeypatch, workspace_root):
    native = setup_native(client, monkeypatch, workspace_root)
    monkeypatch.setattr(client.app.state.db, 'all_chat_metadata', AsyncMock(side_effect=OSError('fixture')))
    response = client.post('/api/threads/source/fork', json={'turn_id': 'early'})
    assert response.status_code == 201 and response.json()['metadataSaved'] is False
    assert native.await_count == 2
