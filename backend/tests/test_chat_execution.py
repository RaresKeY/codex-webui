import pytest
from unittest.mock import AsyncMock
from test_routed_chat import ASK, setup


@pytest.mark.parametrize('model,effort', [('gpt-6.1-sol','high'),('gpt-6-luna','max')])
def test_manual_chat_choice_binds_and_sends_exact_ask_without_jev(client, monkeypatch, model, effort):
    calls = setup(client, monkeypatch)
    choice = {'model':model,'effort':effort}
    assert client.patch('/api/threads/one/execution',json=choice).json() == {**choice,'acknowledged':True}
    assert client.get('/api/threads/one/execution').json() == choice
    assert client.get('/api/threads/two/execution').json()['model'] == 'auto'
    calls.clear()
    response = client.post('/api/threads/one/messages',json={'input':ASK})
    assert response.status_code == 201
    assert response.json()['decision']['policy'] == 'manual'
    assert 'jev' not in [method for method,_ in calls]
    assert calls[-2][1]['model'] == calls[-1][1]['model'] == model
    assert calls[-2][1]['effort'] == calls[-1][1]['effort'] == effort
    assert calls[-1][1]['input'] == [{'type':'text','text':ASK}]
    assert client.patch('/api/threads/one/execution',json={'model':'auto','effort':effort}).status_code == 200
    calls.clear()
    assert client.post('/api/threads/one/messages',json={'input':ASK}).status_code == 201
    assert 'jev' in [method for method,_ in calls]


@pytest.mark.parametrize('payload',[{'model':'other','effort':'high'},{'model':'gpt-6.1-sol','effort':'ultra'},{'model':'auto','extra':True}])
def test_unknown_execution_choices_rejected_before_native(client, monkeypatch, payload):
    calls=setup(client,monkeypatch)
    assert client.patch('/api/threads/one/execution',json=payload).status_code==422
    assert calls==[]


def test_unacknowledged_selection_preserves_auto_and_never_executes(client, monkeypatch):
    calls=setup(client,monkeypatch)
    original=client.app.state.codex.request
    async def request(method,params):
        if method=='thread/settings/update': return {'not':'acknowledged'}
        return await original(method,params)
    monkeypatch.setattr(client.app.state.codex,'request',request)
    assert client.patch('/api/threads/one/execution',json={'model':'gpt-6.1-sol','effort':'high'}).status_code==502
    assert client.get('/api/threads/one/execution').json()['model']=='auto'
    assert not any(method=='turn/start' for method,_ in calls)


def test_new_chat_copies_last_successful_permissions_without_changing_existing_chats(client,monkeypatch):
    setup(client,monkeypatch)
    assert client.patch('/api/threads/one/permissions',json={'mode':'yolo'}).status_code==200
    original=client.app.state.codex.request
    async def request(method,params):
        if method=='thread/start': return {'thread':{'id':'new'}}
        if method=='thread/read': return {'thread':{'id':params['threadId'],'status':{'type':'idle'}}}
        if method=='thread/loaded/list': return {'data':['one','new']}
        return await original(method,params)
    monkeypatch.setattr(client.app.state.codex,'request',AsyncMock(side_effect=request))
    assert client.post('/api/threads',json={}).status_code==201
    assert client.get('/api/threads/new/permissions').json()=={'mode':'yolo'}
    assert client.get('/api/threads/two/permissions').json()=={'mode':'default'}
    assert client.patch('/api/threads/one/permissions',json={'mode':'default'}).status_code==200
    assert client.get('/api/threads/new/permissions').json()=={'mode':'yolo'}
