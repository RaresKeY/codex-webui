import asyncio
import json
from unittest.mock import AsyncMock, PropertyMock

import pytest

from app.chat_service import MessageError
from app.codex_client import CodexRPCError
from app.models import TurnStart
from app.task_router import RoutingError

ASK = " \tKeep these edges.\nUnicode: café 🙂\n\n "
DECISION = {"model": "gpt-6-luna", "effort": "low", "reviewNeeded": False, "policy": "2026-10-05-v5"}


def setup(client, monkeypatch, *, loaded=True, fail=None, decision=None):
    codex = client.app.state.codex
    calls = []

    async def request(method, params):
        calls.append((method, params))
        if method == fail:
            raise CodexRPCError({"message": "upstream private diagnostic"})
        if method == "thread/read":
            return {"thread": {"id": "one", "historyMode": "legacy", "status": {"type": "idle"}}}
        if method == "thread/loaded/list":
            return {"data": ["one"] if loaded else []}
        if method == "turn/start":
            return {"turn": {"id": "t1"}}
        return {}

    async def choose(task):
        calls.append(("jev", task))
        return decision or DECISION.copy()

    monkeypatch.setattr(type(codex), "available", PropertyMock(return_value=True))
    monkeypatch.setattr(codex, "request", AsyncMock(side_effect=request))
    monkeypatch.setattr(client.app.state.router, "choose", AsyncMock(side_effect=choose))
    return calls


@pytest.mark.parametrize("endpoint", ["messages", "turns"])
def test_direct_chat_submission_always_routes_and_preserves_exact_input(client, monkeypatch, endpoint):
    calls = setup(client, monkeypatch)
    response = client.post(f"/api/threads/one/{endpoint}", json={"input": ASK})
    assert response.status_code == 201
    assert response.json()["modelChangeAcknowledged"] is True
    assert [call[0] for call in calls] == ["thread/read", "jev", "thread/loaded/list", "thread/settings/update", "turn/start"]
    assert calls[1][1] == ASK
    assert calls[-2][1] == {"threadId": "one", "model": "gpt-6-luna", "effort": "low"}
    assert calls[-1][1]["input"] == [{"type": "text", "text": ASK}]
    assert calls[-1][1]["model"] == "gpt-6-luna" and calls[-1][1]["effort"] == "low"


@pytest.mark.parametrize("endpoint,extra", [
    ("turns", {"model": "outside-policy"}),
    ("messages", {"model": "gpt-6.1-sol"}),
    ("turns", {"effort": "high"}),
])
def test_execution_rejects_caller_choices_before_any_spending_or_execution(client, monkeypatch, endpoint, extra):
    calls = setup(client, monkeypatch)
    assert client.post(f"/api/threads/one/{endpoint}", json={"input": ASK, **extra}).status_code == 422
    assert calls == []


def test_thread_creation_with_prompt_and_direct_steering_cannot_execute(client, monkeypatch):
    calls = setup(client, monkeypatch)
    assert client.post("/api/threads", json={"prompt": ASK}).status_code == 422
    assert client.post("/api/threads/one/turns/t1/steer", json={"input": ASK}).status_code == 409
    assert calls == []


def test_unloaded_thread_is_resumed_then_acknowledged_before_execution(client, monkeypatch):
    calls = setup(client, monkeypatch, loaded=False)
    response = client.post("/api/threads/one/messages", json={"input": ASK})
    assert response.status_code == 201
    assert [call[0] for call in calls][-3:] == ["thread/resume", "thread/settings/update", "turn/start"]
    assert calls[-3][1] == {"threadId": "one", "excludeTurns": True}


@pytest.mark.parametrize("fail", ["thread/resume", "thread/settings/update"])
def test_failed_loading_or_model_change_never_executes_or_retries(client, monkeypatch, fail):
    calls = setup(client, monkeypatch, loaded=False, fail=fail)
    response = client.post("/api/threads/one/messages", json={"input": ASK})
    assert response.status_code == 502
    assert "private" not in response.text
    assert not any(method == "turn/start" for method, _ in calls)
    assert sum(method == "jev" for method, _ in calls) == 1
    assert sum(method == fail for method, _ in calls) == 1


def test_routing_failure_never_changes_model_or_executes(client, monkeypatch):
    calls = setup(client, monkeypatch)
    client.app.state.router.choose.side_effect = RoutingError("Jev failed safely")
    response = client.post("/api/threads/one/turns", json={"input": ASK})
    assert response.status_code == 409
    assert [method for method, _ in calls] == ["thread/read"]
    assert client.app.state.router.choose.await_count == 1


def test_metadata_is_not_accepted_as_a_model_change_acknowledgement(client, monkeypatch):
    calls = setup(client, monkeypatch)
    original = client.app.state.codex.request
    async def request(method, params):
        if method == "thread/settings/update":
            return {"thread": {"id": "one"}}
        return await original(method, params)
    monkeypatch.setattr(client.app.state.codex, "request", request)
    assert client.post("/api/threads/one/messages", json={"input": ASK}).status_code == 502
    assert not any(method == "turn/start" for method, _ in calls)


@pytest.mark.parametrize("decision", [
    {**DECISION, "model": "outside-policy"},
    {**DECISION, "effort": "high", "reviewNeeded": False},
])
def test_backend_rejects_invalid_or_conflicting_choices_independently_of_browser(client, monkeypatch, decision):
    calls = setup(client, monkeypatch, decision=decision)
    assert client.post("/api/threads/one/messages", json={"input": ASK}).status_code == 409
    assert [method for method, _ in calls] == ["thread/read", "jev"]


def test_stream_reports_server_stages_and_result_from_one_request(client, monkeypatch):
    calls = setup(client, monkeypatch)
    response = client.post("/api/threads/one/messages", json={"input": ASK}, headers={"Accept": "application/x-ndjson"})
    frames = [json.loads(line) for line in response.text.splitlines()]
    assert response.status_code == 201
    assert [frame["stage"] for frame in frames[:-1]] == ["routing", "switching", "sending"]
    assert frames[-1]["result"]["modelChangeAcknowledged"] is True
    assert sum(method == "jev" for method, _ in calls) == 1


def test_stream_error_never_reports_a_successful_turn(client, monkeypatch):
    calls = setup(client, monkeypatch, fail="thread/settings/update")
    response = client.post("/api/threads/one/messages", json={"input": ASK}, headers={"Accept": "application/x-ndjson"})
    frames = [json.loads(line) for line in response.text.splitlines()]
    assert frames[-1]["error"]["status"] == 502
    assert not any("result" in frame for frame in frames)
    assert not any(method == "turn/start" for method, _ in calls)


@pytest.mark.asyncio
async def test_cancellation_and_concurrent_submission_stop_before_binding(client, monkeypatch):
    calls = setup(client, monkeypatch)
    operation = client.app.state.chat.send("one", TurnStart(input=ASK))
    assert (await anext(operation))["stage"] == "routing"
    duplicate = client.app.state.chat.send("one", TurnStart(input=ASK))
    with pytest.raises(MessageError, match="already being submitted"):
        await anext(duplicate)
    assert (await anext(operation))["stage"] == "switching"
    await operation.aclose()
    assert not any(method in {"thread/settings/update", "turn/start"} for method, _ in calls)
    assert client.app.state.chat._sending == set()


@pytest.mark.asyncio
async def test_turn_waits_for_the_actual_model_acknowledgement(client, monkeypatch):
    calls = setup(client, monkeypatch)
    original = client.app.state.codex.request
    acknowledge = asyncio.Event()
    binding_started = asyncio.Event()

    async def delayed(method, params):
        if method == "thread/settings/update":
            binding_started.set()
            await acknowledge.wait()
        return await original(method, params)

    monkeypatch.setattr(client.app.state.codex, "request", delayed)
    async def consume():
        return [frame async for frame in client.app.state.chat.send("one", TurnStart(input=ASK))]
    pending = asyncio.create_task(consume())
    await asyncio.wait_for(binding_started.wait(), 2)
    assert not any(method == "turn/start" for method, _ in calls)
    acknowledge.set()
    frames = await asyncio.wait_for(pending, 2)
    assert frames[-1]["result"]["turn"]["id"] == "t1"
