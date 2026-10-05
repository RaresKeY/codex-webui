from unittest.mock import AsyncMock, PropertyMock

import pytest

from app.codex_client import CodexRPCError
from app.plugins import PluginError


def catalog():
    return {"marketplaces": [{"name": "local", "plugins": [
        {"id": "notes@local", "name": "notes", "installed": True, "enabled": True,
         "availability": "AVAILABLE", "source": "private path", "interface": {"displayName": "Notes", "shortDescription": "Find notes"}},
        {"id": "off@local", "name": "off", "installed": True, "enabled": False},
        {"id": "missing@local", "name": "missing", "installed": False, "enabled": True},
        {"id": "blocked@local", "name": "blocked", "installed": True, "enabled": True, "availability": "DISABLED_BY_ADMIN"},
    ]}], "marketplaceLoadErrors": []}


def test_installed_plugins_are_filtered_and_sanitized(client, monkeypatch):
    request = AsyncMock(return_value=catalog())
    monkeypatch.setattr(client.app.state.codex, "request", request)
    response = client.get("/api/plugins")
    assert response.status_code == 200
    assert response.json() == {"data": [{"id": "notes@local", "name": "notes", "displayName": "Notes", "description": "Find notes"}]}
    request.assert_awaited_once_with("plugin/installed", {"cwds": [str(client.app.state.settings.workspace_root)]})
    assert client.get("/api/plugins", params={"cwd": "../outside"}).status_code == 503
    assert request.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("result", [{}, {"marketplaces": [{"plugins": None}]}, {"marketplaces": [], "marketplaceLoadErrors": [{}]}])
async def test_invalid_or_failed_catalog_is_not_reported_as_empty(client, monkeypatch, result):
    monkeypatch.setattr(client.app.state.codex, "request", AsyncMock(return_value=result))
    with pytest.raises(PluginError):
        await client.app.state.plugins.entries(".")


def test_plugin_rpc_error_does_not_expose_diagnostics(client, monkeypatch):
    monkeypatch.setattr(client.app.state.codex, "request", AsyncMock(side_effect=CodexRPCError({"message": "private diagnostic"})))
    response = client.get("/api/plugins")
    assert response.status_code == 503 and "private diagnostic" not in response.text


@pytest.mark.parametrize("identifier,ask", [("missing@local", "@missing hi"), ("notes@local", "user@notes hi"), ("notes@local", "@notes-more hi"), ("plugin://notes@local", "@notes hi")])
def test_unavailable_or_unmentioned_plugin_stops_before_jev(client, monkeypatch, identifier, ask):
    calls = configure_send(client, monkeypatch)
    response = client.post("/api/threads/one/messages", json={"input": ask, "plugins": [identifier]})
    assert response.status_code == 409
    assert calls == ["thread/read", "plugin/installed"]


def configure_send(client, monkeypatch):
    codex = client.app.state.codex
    calls = []
    async def request(method, params):
        calls.append(method)
        if method == "plugin/installed": return catalog()
        if method == "thread/read": return {"thread": {"id": "one", "cwd": str(client.app.state.settings.workspace_root), "status": "idle"}}
        if method == "thread/loaded/list": return {"data": ["one"]}
        if method == "turn/start": return {"turn": {"id": "t1"}}
        return {}
    async def choose(ask):
        calls.append("jev")
        return {"model": "gpt-6-luna", "effort": "low"}
    monkeypatch.setattr(type(codex), "available", PropertyMock(return_value=True))
    monkeypatch.setattr(codex, "request", AsyncMock(side_effect=request))
    monkeypatch.setattr(client.app.state.router, "choose", AsyncMock(side_effect=choose))
    return calls


def test_exact_ask_and_native_mentions_follow_routing_and_acknowledgement(client, monkeypatch):
    calls = configure_send(client, monkeypatch)
    ask = " \tUse @notes to find this.\n\n "
    response = client.post("/api/threads/one/messages", json={"input": ask, "plugins": ["notes@local"]})
    assert response.status_code == 201
    assert calls == ["thread/read", "plugin/installed", "jev", "thread/loaded/list", "thread/settings/update", "turn/start"]
    client.app.state.router.choose.assert_awaited_once_with(ask)
    assert client.app.state.codex.request.call_args.args[1]["input"] == [
        {"type": "text", "text": ask}, {"type": "mention", "name": "notes", "path": "plugin://notes@local"},
    ]


def test_duplicate_plugins_and_arbitrary_native_inputs_are_rejected(client):
    assert client.post("/api/threads/one/messages", json={"input": "@notes", "plugins": ["notes@local"] * 2}).status_code == 422
    assert client.post("/api/threads/one/messages", json={"input": "@notes", "mentions": [{"path": "/private"}]}).status_code == 422
