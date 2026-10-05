from copy import deepcopy
import sqlite3
from unittest.mock import AsyncMock, PropertyMock

import pytest

from app.codex_client import CodexRPCError


def configure(client, monkeypatch):
    root = client.app.state.settings.workspace_root
    (root / "src").mkdir()
    (root / "src/main.py").write_text("print('fixture')")
    skill = str(root.parent / "skills/review/SKILL.md")
    responses = {
        "skills/list": {"data": [{"cwd": str(root), "skills": [
            {"name": "review", "enabled": True, "path": skill, "description": "Review changes", "pluginId": None},
            {"name": "disabled", "enabled": False, "path": "/private/disabled"},
        ], "errors": []}]},
        "plugin/installed": {"marketplaces": [{"plugins": [{"id": "notes@local", "name": "notes", "installed": True, "enabled": True}]}]},
        "app/installed": {"apps": [{"id": "drive", "runtimeName": "Drive", "enabled": True, "callable": True},
                                    {"id": "blocked", "enabled": True, "callable": False}]},
        "app/read": {"apps": [{"id": "drive", "name": "Google Drive", "description": "Find documents"}]},
        "fuzzyFileSearch": {"files": [{"root": str(root), "path": "src/main.py"}]},
        "thread/read": {"thread": {"id": "one", "cwd": str(root), "status": "idle", "turns": [{"id": "t1", "items": []}]}},
        "thread/loaded/list": {"data": ["one"]},
        "turn/start": {"turn": {"id": "t1"}},
    }
    calls = []
    async def request(method, params):
        calls.append((method, params))
        return deepcopy(responses.get(method, {}))
    monkeypatch.setattr(client.app.state.codex, "request", AsyncMock(side_effect=request))
    monkeypatch.setattr(type(client.app.state.codex), "available", PropertyMock(return_value=True))
    monkeypatch.setattr(client.app.state.router, "choose", AsyncMock(return_value={"model": "gpt-6.1-sol", "effort": "high"}))
    return responses, calls, skill


def test_catalog_projects_enabled_native_entries_without_native_paths(client, monkeypatch):
    _, calls, skill = configure(client, monkeypatch)
    response = client.get("/api/mentions", params={"thread_id": "one"})
    assert response.status_code == 200
    result = response.json()
    assert result["errors"] == []
    assert {entry["kind"] for entry in result["data"]} == {"skill", "plugin", "app"}
    assert {entry["insertText"] for entry in result["data"]} == {"$review", "@notes", "$google-drive"}
    assert skill not in response.text and "native" not in response.text
    assert ("app/installed", {"threadId": "one"}) in calls
    before = len(calls)
    assert client.get("/api/mentions", params={"cwd": "../outside"}).status_code == 503
    assert len(calls) == before


def test_unavailable_category_is_explicit_and_keeps_other_mentions(client, monkeypatch):
    configure(client, monkeypatch)
    request = client.app.state.codex.request.side_effect
    async def fail_apps(method, params):
        if method == "app/installed": raise CodexRPCError({"message": "private diagnostic"})
        return await request(method, params)
    client.app.state.codex.request.side_effect = fail_apps
    response = client.get("/api/mentions")
    assert response.status_code == 200 and "private diagnostic" not in response.text
    assert {entry["kind"] for entry in response.json()["data"]} == {"skill", "plugin"}
    assert response.json()["errors"][0]["kind"] == "app"


def test_partial_skill_errors_keep_usable_skills_and_hide_diagnostics(client, monkeypatch):
    responses, _, _ = configure(client, monkeypatch)
    responses["skills/list"]["data"][0]["errors"] = [{"message": "private diagnostic"}]
    result = client.get("/api/mentions")
    assert "private diagnostic" not in result.text
    assert any(entry["kind"] == "skill" for entry in result.json()["data"])
    assert result.json()["errors"][0]["kind"] == "skill"


def test_app_discovery_for_unloaded_history_uses_global_snapshot(client, monkeypatch):
    responses, calls, _ = configure(client, monkeypatch)
    responses["thread/loaded/list"] = {"data": []}
    result = client.get("/api/mentions", params={"thread_id": "one"})
    assert result.json()["errors"] == []
    assert ("app/installed", {}) in calls
    assert not any(method == "thread/resume" for method, _ in calls)


def test_selected_app_is_revalidated_with_effective_thread_config_before_jev(client, monkeypatch):
    responses, calls, _ = configure(client, monkeypatch)
    responses["thread/loaded/list"] = {"data": []}
    request = client.app.state.codex.request.side_effect
    async def with_thread_config(method, params):
        if method == "thread/resume":
            responses["thread/loaded/list"] = {"data": ["one"]}
        if method == "app/installed" and params.get("threadId") == "one":
            responses["app/installed"]["apps"][0]["callable"] = False
        return await request(method, params)
    client.app.state.codex.request.side_effect = with_thread_config
    response = client.post("/api/threads/one/messages", json={"input": "$google-drive", "mentions": ["app:drive"]})
    assert response.status_code == 409
    assert ("thread/resume", {"threadId": "one", "excludeTurns": True}) in calls
    assert ("app/installed", {"threadId": "one"}) in calls
    client.app.state.router.choose.assert_not_awaited()


def test_plugin_skill_namespace_and_quoted_file_reference(client, monkeypatch):
    responses, calls, skill = configure(client, monkeypatch)
    responses["skills/list"]["data"][0]["skills"][0]["pluginId"] = "notes@local"
    root = client.app.state.workspace.root
    (root / "src/my file.py").write_text("fixture")
    responses["fuzzyFileSearch"]["files"] = [{"root": str(root), "path": "src/my file.py"}]
    catalog = client.get("/api/mentions").json()["data"]
    selected = next(entry for entry in catalog if entry["kind"] == "skill")
    assert selected["insertText"] == "$notes:review"
    file = client.get("/api/mention-files", params={"q": "file"}).json()["data"][0]
    assert file["insertText"] == '@"src/my file.py"'
    ask = '$notes:review check @"src/my file.py".'
    response = client.post("/api/threads/one/messages", json={"input": ask, "mentions": [selected["id"], file["id"]]})
    assert response.status_code == 201
    assert calls[-1][1]["input"] == [{"type": "text", "text": ask}, {"type": "skill", "name": "review", "path": skill}]


def test_selected_skills_apps_plugins_and_files_preserve_ask_and_routing(client, monkeypatch):
    _, calls, skill = configure(client, monkeypatch)
    catalog = client.get("/api/mentions", params={"thread_id": "one"}).json()["data"]
    files = client.get("/api/mention-files", params={"q": "main"}).json()["data"]
    assert files[0]["insertText"] == "@src/main.py"
    ask = " \t$review @notes $google-drive @src/main.py\n\n "
    calls.clear()
    response = client.post("/api/threads/one/messages", json={"input": ask, "mentions": [entry["id"] for entry in [*catalog, *files]]})
    assert response.status_code == 201 and response.json()["selectionSaved"] is True
    client.app.state.router.choose.assert_awaited_once_with(ask)
    assert [method for method, _ in calls][-3:] == ["thread/loaded/list", "thread/settings/update", "turn/start"]
    inputs = calls[-1][1]["input"]
    assert inputs[0] == {"type": "text", "text": ask}
    assert {tuple(sorted(item.items())) for item in inputs[1:]} == {
        tuple(sorted({"type": "skill", "name": "review", "path": skill}.items())),
        tuple(sorted({"type": "mention", "name": "notes", "path": "plugin://notes@local"}.items())),
        tuple(sorted({"type": "mention", "name": "Google Drive", "path": "app://drive"}.items())),
    }
    history = client.get("/api/threads/one").json()
    assert history["thread"]["turns"][0]["webui"] == {"model": "gpt-6.1-sol", "effort": "high"}


@pytest.mark.parametrize("identifier,ask", [("skill:fake", "$review"), ("app:blocked", "$blocked"),
                                          ("plugin:notes@local", "person@notes"), ("file:..%2Foutside", "@outside"),
                                          ("app:drive", "$google-drive-more"), ("app:drive", "é$google-drive")])
def test_invalid_mentions_never_spend_or_execute(client, monkeypatch, identifier, ask):
    _, calls, _ = configure(client, monkeypatch)
    response = client.post("/api/threads/one/messages", json={"input": ask, "mentions": [identifier]})
    assert response.status_code == 409
    client.app.state.router.choose.assert_not_awaited()
    assert not any(method == "turn/start" for method, _ in calls)


def test_file_search_filters_protected_and_escaped_native_results(client, monkeypatch):
    responses, _, _ = configure(client, monkeypatch)
    root = client.app.state.workspace.root
    protected = root / ".env"
    protected.write_text("synthetic-fixture")
    client.app.state.workspace.protected_paths = (protected,)
    (root / "alias").symlink_to(protected)
    responses["fuzzyFileSearch"]["files"].extend({"root": str(root), "path": path} for path in (".env", "alias", "../outside"))
    result = client.get("/api/mention-files", params={"q": "main"})
    assert result.status_code == 200
    assert len(result.json()["data"]) == 1
    assert client.post("/api/threads/one/messages", json={"input": "@.env", "mentions": ["file:.env"]}).status_code == 409
    client.app.state.router.choose.assert_not_awaited()


def test_combined_selection_limit_and_duplicate_alias_are_rejected(client):
    assert client.post("/api/threads/one/messages", json={"input": "ask", "plugins": [str(i) for i in range(8)], "mentions": ["app:drive"]}).status_code == 422
    assert client.post("/api/threads/one/messages", json={"input": "@notes", "plugins": ["notes@local"], "mentions": ["plugin:notes@local"]}).status_code == 422


def test_metadata_failure_cannot_turn_an_acknowledged_submission_into_a_retry(client, monkeypatch):
    _, calls, _ = configure(client, monkeypatch)
    monkeypatch.setattr(client.app.state.db, "record_turn_selection", AsyncMock(side_effect=sqlite3.OperationalError("private diagnostic")))
    response = client.post("/api/threads/one/messages", json={"input": "ask"})
    assert response.status_code == 201 and response.json()["selectionSaved"] is False
    assert "private diagnostic" not in response.text
    assert sum(method == "turn/start" for method, _ in calls) == 1


def test_selection_read_failure_preserves_native_history(client, monkeypatch):
    configure(client, monkeypatch)
    monkeypatch.setattr(client.app.state.db, "turn_selections", AsyncMock(side_effect=sqlite3.OperationalError("private diagnostic")))
    response = client.get("/api/threads/one")
    assert response.status_code == 200
    assert response.json()["thread"]["turns"] == [{"id": "t1", "items": []}]
    assert "private diagnostic" not in response.text
