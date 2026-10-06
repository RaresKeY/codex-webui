import json
import sqlite3
from unittest.mock import AsyncMock, PropertyMock

import pytest

from app.database import Database
from app.jev_activity import JevActivity, activity_page
from app.task_router import RoutingError

DECISION = {"model": "gpt-6-luna", "effort": "low", "policy": "fixture-policy", "modelConfidence": .8,
            "effortConfidence": .9, "usage": {"input_tokens": 20, "output_tokens": 10},
            "modelProbabilities": {"gpt-6-luna": .8, "gpt-6.1-sol": .2}, "private_provider_body": "secret fixture",
            "preparation": {"online_search": {"choice": "yes", "confidence": .8, "probabilities": {"yes": .8, "no": .1, "unclear": .1}, "raw_prompt": "private ask"}}}


def configure(client, monkeypatch, failure=None):
    async def native(method, params):
        if method == "thread/read":
            return {"thread": {"id": "chat", "turns": [{"id": "actual-turn", "status": "completed", "items": [{"text": "private output"}]}]}}
        if method == "thread/loaded/list":
            return {"data": ["chat"]}
        if method == "thread/settings/update" and failure == "ack":
            return {"unexpected": "private diagnostic"}
        if method == "turn/start":
            return {"turn": {"id": "actual-turn"}}
        return {}
    monkeypatch.setattr(type(client.app.state.codex), "available", PropertyMock(return_value=True))
    monkeypatch.setattr(client.app.state.codex, "request", AsyncMock(side_effect=native))
    monkeypatch.setattr(client.app.state.router, "choose", AsyncMock(return_value=DECISION.copy()))


def test_submitted_activity_links_actual_turn_and_never_stores_content(client, monkeypatch):
    configure(client, monkeypatch)
    assert client.post("/api/threads/chat/messages", json={"input": "private ask"}).status_code == 201
    page = client.get("/api/jev/activity").json()
    item = page["data"][0]
    assert (item["status"], item["source"], item["turn_id"]) == ("submitted", "auto", "actual-turn")
    assert item["decision"]["usage"] == {"input_tokens": 20, "output_tokens": 10}
    assert item["decision"]["preparation"]["online_search"] == {"choice": "yes", "confidence": .8, "probabilities": {"yes": .8, "no": .1, "unclear": .1}}
    assert "private" not in json.dumps(page) and "secret" not in json.dumps(page)
    result = client.get(f'/api/jev/activity/{item["id"]}/turn')
    assert result.json() == {"threadId": "chat", "turnId": "actual-turn", "status": "completed"}
    client.portal.call(client.app.state.db.delete_chat_state, "chat")
    assert client.get("/api/jev/activity").json()["data"] == []
    assert client.get(f'/api/jev/activity/{item["id"]}/turn').status_code == 404


@pytest.mark.parametrize("failure,stage", [("route", "routing"), ("ack", "switching")])
def test_failed_attempt_is_visible_without_claiming_a_turn(client, monkeypatch, failure, stage):
    configure(client, monkeypatch, failure)
    if failure == "route":
        client.app.state.router.choose.side_effect = RoutingError("Routing failed safely")
    assert client.post("/api/threads/chat/messages", json={"input": "private ask"}).status_code in {409, 502}
    item = client.get("/api/jev/activity").json()["data"][0]
    assert (item["status"], item["stage"], item["turn_id"]) == ("stopped", stage, None)
    assert not any(call.args[0] == "turn/start" for call in client.app.state.codex.request.await_args_list)


def test_preview_is_recorded_without_execution_and_manual_turn_skips_jev(client, monkeypatch):
    configure(client, monkeypatch)
    assert client.post("/api/threads/chat/route", json={"input": "private ask"}).status_code == 200
    assert client.app.state.codex.request.await_count == 0
    assert client.patch("/api/threads/chat/execution", json={"model": "gpt-6.1-sol", "effort": "medium"}).status_code == 200
    assert client.post("/api/threads/chat/messages", json={"input": "manual ask"}).status_code == 201
    items = client.get("/api/jev/activity").json()["data"]
    assert [(item["source"], item["status"]) for item in items] == [("manual", "submitted"), ("preview", "classified")]
    assert items[0]["decision"] == {"model": "gpt-6.1-sol", "effort": "medium", "policy": "manual"}
    assert client.app.state.router.choose.await_count == 1


def test_activity_write_failure_does_not_cause_false_send_failure(client, monkeypatch):
    configure(client, monkeypatch)
    original = client.app.state.db.execute
    async def execute(sql, params=()):
        if "jev_activity" in sql:
            raise sqlite3.OperationalError("fixture storage failure")
        return await original(sql, params)
    monkeypatch.setattr(client.app.state.db, "execute", execute)
    assert client.post("/api/threads/chat/messages", json={"input": "ask"}).status_code == 201
    assert sum(call.args[0] == "turn/start" for call in client.app.state.codex.request.await_args_list) == 1


@pytest.mark.asyncio
async def test_activity_pagination_reopen_and_stale_pending(tmp_path):
    db = Database(tmp_path / "activity.sqlite3")
    await db.initialize()
    for index in range(5):
        activity = JevActivity(db)
        await activity.begin("chat", "auto")
        if index < 4:
            await activity.update("submitted", "sending", DECISION, str(index))
    first = await activity_page(db, None, 2)
    assert [item["id"] for item in first["data"]] == [5, 4]
    newer = JevActivity(db)
    await newer.begin("other", "preview")
    await newer.update("classified", "routing", DECISION)
    second = await activity_page(db, first["nextCursor"], 2)
    assert [item["id"] for item in second["data"]] == [3, 2]
    last = await activity_page(db, second["nextCursor"], 2)
    assert [item["id"] for item in last["data"]] == [1] and last["nextCursor"] is None
    await Database(db.path).initialize()
    assert (await db.fetchone("SELECT status FROM jev_activity WHERE id=5"))["status"] == "interrupted"


def test_invalid_pagination_and_missing_turn_are_safe(client):
    assert client.get("/api/jev/activity?limit=101").status_code == 422
    assert client.get("/api/jev/activity?before=0").status_code == 422
    assert client.get("/api/jev/activity/1/turn").status_code == 404


def test_jev_stage_events_are_thread_scoped_safe_and_ordered(client, monkeypatch):
    configure(client, monkeypatch)
    publish = AsyncMock()
    monkeypatch.setattr(client.app.state.codex, '_publish', publish)
    assert client.post('/api/threads/chat/messages', json={'input': 'private ask'}).status_code == 201
    events = [call.args[0] for call in publish.await_args_list if call.args[0]['method'] == 'webui/jevActivity']
    assert [event['params']['activity']['stage'] for event in events] == ['routing', 'routing', 'switching', 'sending', 'sending']
    assert all(event['params']['threadId'] == 'chat' for event in events)
    assert events[0]['params']['activity']['decision'] is None
    assert events[-1]['params']['activity']['turn_id'] == 'actual-turn'
    assert events[-1]['params']['activity']['status'] == 'submitted'
    assert 'private' not in json.dumps(events) and 'secret' not in json.dumps(events)
    assert client.get('/api/threads/other/jev/activity').json() == {'data': [], 'nextCursor': None}
    assert client.get('/api/threads/chat/jev/activity').json()['data'][0]['id'] == events[0]['params']['activity']['id']
    assert client.post('/api/threads/chat/route', json={'input': 'preview ask'}).status_code == 200
    assert len(client.get('/api/threads/chat/jev/activity').json()['data']) == 1


def test_stopped_jev_attempt_emits_final_state_without_inventing_turn(client, monkeypatch):
    configure(client, monkeypatch, 'ack')
    publish = AsyncMock()
    monkeypatch.setattr(client.app.state.codex, '_publish', publish)
    assert client.post('/api/threads/chat/messages', json={'input': 'private ask'}).status_code == 502
    last = publish.await_args_list[-1].args[0]['params']['activity']
    assert (last['status'], last['stage'], last['turn_id']) == ('stopped', 'switching', None)
    assert client.get('/api/threads/chat/jev/activity?limit=101').status_code == 422


def test_activity_socket_delivers_jev_events_without_transcript_deltas(client):
    import time
    event = {'method': 'webui/jevActivity', 'params': {'threadId': 'chat', 'activity': {'id': 1}}}
    with client.websocket_connect('/api/activity') as socket:
        assert socket.receive_json()['method'] == 'webui/status'
        for _ in range(100):
            if client.app.state.codex._subscribers:
                break
            time.sleep(.01)
        assert client.app.state.codex._subscribers
        client.portal.call(client.app.state.codex._publish, {'method': 'item/agentMessage/delta', 'params': {'threadId': 'chat', 'delta': 'private'}})
        client.portal.call(client.app.state.codex._publish, event)
        assert socket.receive_json() == event
