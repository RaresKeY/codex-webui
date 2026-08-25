from __future__ import annotations

import subprocess
from unittest.mock import AsyncMock, PropertyMock

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import event_is_for_thread, event_thread_id
from app.codex_client import CodexRPCError


def test_bootstrap_and_degraded_threads(client: TestClient) -> None:
    bootstrap = client.get("/api/bootstrap")
    assert bootstrap.status_code == 200
    assert bootstrap.json()["health"]["status"] == "degraded"
    assert bootstrap.json()["system"]["runtime"] == "localhost-companion"
    assert bootstrap.json()["features"]["hostCompanion"] is True
    response = client.get("/api/threads")
    assert response.status_code == 200
    assert response.json()["data"] == []
    assert response.json()["degraded"] is True


def test_project_setting_and_metadata_crud(client: TestClient) -> None:
    workspace_root = client.app.state.settings.workspace_root
    (workspace_root / "project-a").mkdir()
    created = client.post(
        "/api/projects",
        json={"name": "WebUI", "description": "Local Codex", "workspace": "project-a"},
    )
    assert created.status_code == 201
    project_id = created.json()["id"]
    assert created.json()["workspace"] == "project-a"
    metadata = client.patch(
        "/api/threads/thread-1/metadata",
        json={"project_id": project_id, "pinned": True},
    )
    assert metadata.status_code == 200
    assert metadata.json()["pinned"] == 1
    assert client.put("/api/settings/theme", json={"value": "dark"}).status_code == 200
    assert client.get("/api/settings").json() == {"theme": "dark"}
    assert client.delete(f"/api/projects/{project_id}").status_code == 204
    assert client.post(
        "/api/projects", json={"name": "Escape", "workspace": "../outside"}
    ).status_code == 400


def test_scheduled_task_crud(client: TestClient) -> None:
    created = client.post(
        "/api/tasks",
        json={
            "name": "Periodic status",
            "prompt": "Summarize status",
            "schedule_type": "interval",
            "schedule": "60",
            "workspace": ".",
            "enabled": True,
        },
    )
    assert created.status_code == 201, created.text
    task_id = created.json()["id"]
    assert client.patch(f"/api/tasks/{task_id}", json={"enabled": False}).status_code == 200
    assert client.delete(f"/api/tasks/{task_id}").status_code == 204


def test_workspace_traversal_via_api_is_forbidden(client: TestClient) -> None:
    assert client.get("/api/workspace/file", params={"path": "../escape"}).status_code == 403
    assert client.put(
        "/api/workspace/file", params={"path": "../escape"}, json={"content": "x"}
    ).status_code == 403


def test_workspace_changes_use_bounded_read_only_git_adapter(client: TestClient) -> None:
    workspace_root = client.app.state.settings.workspace_root
    repo = workspace_root / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "tracked.txt").write_text("before\n")
    subprocess.run(["git", "-C", str(repo), "add", "tracked.txt"], check=True)
    subprocess.run([
        "git", "-C", str(repo), "-c", "user.name=Codex WebUI Test",
        "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture",
    ], check=True)
    (repo / "tracked.txt").write_text("after\n")
    (repo / "new.txt").write_text("new\n")

    response = client.get("/api/workspace/changes", params={"path": str(repo)})

    assert response.status_code == 200
    assert response.json()["repoRoot"] == "repo"
    assert {item["path"]: item["status"] for item in response.json()["data"]} == {
        "repo/new.txt": "added",
        "repo/tracked.txt": "modified",
    }
    assert client.get(
        "/api/workspace/changes", params={"path": str(workspace_root.parent)}
    ).status_code == 403


def test_update_is_gated(client: TestClient) -> None:
    response = client.post("/api/system/update")
    assert response.status_code == 403


def test_event_thread_id_handles_known_envelopes() -> None:
    assert event_thread_id({"params": {"threadId": "a"}}) == "a"
    assert event_thread_id({"params": {"turn": {"threadId": "b"}}}) == "b"
    assert event_thread_id({"params": {"item": {"thread_id": "c"}}}) == "c"
    assert event_thread_id({"params": {"rateLimits": {}}}) is None
    assert event_is_for_thread({"method": "turn/started", "params": {}}, "a") is False
    assert event_is_for_thread({"method": "account/updated", "params": {}}, "a") is True
    assert event_is_for_thread(
        {"method": "turn/completed", "params": {"threadId": "b"}}, "a"
    ) is False


def test_thread_list_forwards_search_and_recency_sort(client: TestClient, monkeypatch) -> None:
    codex = client.app.state.codex
    request = AsyncMock(return_value={"data": []})
    monkeypatch.setattr(codex, "request", request)
    monkeypatch.setattr(type(codex), "available", PropertyMock(return_value=True))
    response = client.get("/api/threads", params={"q": "needle", "limit": 17})
    assert response.status_code == 200
    request.assert_awaited_once_with(
        "thread/list",
        {
            "limit": 17,
            "archived": False,
            "sortKey": "recency_at",
            "sortDirection": "desc",
            "searchTerm": "needle",
        },
    )


def test_background_terminal_inventory_is_thread_scoped_and_read_only(
    client: TestClient, monkeypatch
) -> None:
    codex = client.app.state.codex
    request = AsyncMock(return_value={"data": [{
        "itemId": "item-1", "processId": "42", "command": "pnpm test",
        "cwd": "/workspace/app", "osPid": 100, "cpuPercent": 2.5, "rssKb": 4096,
    }]})
    monkeypatch.setattr(codex, "request", request)
    monkeypatch.setattr(type(codex), "available", PropertyMock(return_value=True))

    response = client.get("/api/threads/thread-1/background-terminals")

    assert response.status_code == 200
    assert response.json()["data"][0]["processId"] == "42"
    request.assert_awaited_once_with(
        "thread/backgroundTerminals/list", {"threadId": "thread-1", "limit": 100}
    )


def test_background_terminal_inventory_resumes_an_unloaded_thread(
    client: TestClient, monkeypatch
) -> None:
    codex = client.app.state.codex
    request = AsyncMock(side_effect=[
        CodexRPCError({"code": -32600, "message": "thread not found: thread-1"}),
        {"thread": {"id": "thread-1"}},
        {"data": []},
    ])
    monkeypatch.setattr(codex, "request", request)
    monkeypatch.setattr(type(codex), "available", PropertyMock(return_value=True))

    response = client.get("/api/threads/thread-1/background-terminals")

    assert response.status_code == 200
    assert response.json() == {"data": []}
    assert request.await_args_list[1].args == (
        "thread/resume", {"threadId": "thread-1"}
    )


def test_background_terminal_inventory_reports_an_external_active_writer(
    client: TestClient, monkeypatch
) -> None:
    codex = client.app.state.codex
    request = AsyncMock(side_effect=[
        CodexRPCError({"code": -32600, "message": "thread not found: thread-1"}),
        CodexRPCError({
            "code": -32600,
            "message": "thread thread-1 already has an active writer",
        }),
    ])
    monkeypatch.setattr(codex, "request", request)
    monkeypatch.setattr(type(codex), "available", PropertyMock(return_value=True))

    response = client.get("/api/threads/thread-1/background-terminals")

    assert response.status_code == 200
    assert response.json() == {
        "data": [],
        "unavailableReason": (
            "Background process activity is owned by another local Codex session."
        ),
    }


def test_unmaterialized_new_thread_reads_metadata_without_turns(
    client: TestClient, monkeypatch
) -> None:
    codex = client.app.state.codex
    request = AsyncMock(side_effect=[
        CodexRPCError({"code": -32600, "message": "thread new-1 is not materialized yet; includeTurns is unavailable before first user message"}),
        {"thread": {"id": "new-1", "turns": []}},
    ])
    monkeypatch.setattr(codex, "request", request)
    monkeypatch.setattr(type(codex), "available", PropertyMock(return_value=True))

    response = client.get("/api/threads/new-1")

    assert response.status_code == 200
    assert response.json() == {"thread": {"id": "new-1", "turns": []}}
    assert request.await_args_list[0].args == (
        "thread/read", {"threadId": "new-1", "includeTurns": True}
    )
    assert request.await_args_list[1].args == (
        "thread/read", {"threadId": "new-1", "includeTurns": False}
    )


def test_unmaterialized_new_thread_resume_is_a_verified_noop(
    client: TestClient, monkeypatch
) -> None:
    codex = client.app.state.codex
    request = AsyncMock(side_effect=[
        CodexRPCError({"code": -32600, "message": "no rollout found for thread id new-1"}),
        {"thread": {"id": "new-1", "turns": []}},
    ])
    monkeypatch.setattr(codex, "request", request)
    monkeypatch.setattr(type(codex), "available", PropertyMock(return_value=True))

    response = client.post("/api/threads/new-1/resume", json={"model": "gpt-5.6-sol"})

    assert response.status_code == 200
    assert response.json()["thread"]["id"] == "new-1"
    assert request.await_args_list[0].args == (
        "thread/resume", {"threadId": "new-1", "model": "gpt-5.6-sol"}
    )
    assert request.await_args_list[1].args == (
        "thread/read", {"threadId": "new-1", "includeTurns": False}
    )


def test_manual_duplicate_task_run_returns_conflict(client: TestClient, monkeypatch) -> None:
    created = client.post(
        "/api/tasks",
        json={
            "name": "Manual", "prompt": "Run", "schedule_type": "interval",
            "schedule": "60", "enabled": False,
        },
    )
    task_id = created.json()["id"]
    monkeypatch.setattr(client.app.state.scheduler, "launch_task", lambda _: False)
    response = client.post(f"/api/tasks/{task_id}/run")
    assert response.status_code == 409


def test_security_headers_and_cross_site_rejection(client: TestClient) -> None:
    response = client.get("/api/health")
    assert "base-uri 'none'" in response.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"] == "microphone=(self)"
    rejected = client.post(
        "/api/projects",
        json={"name": "Cross site"},
        headers={"origin": "https://evil.example", "sec-fetch-site": "cross-site"},
    )
    assert rejected.status_code == 403
    assert rejected.headers["x-frame-options"] == "DENY"


def test_untrusted_host_is_rejected(client: TestClient) -> None:
    assert client.get("/api/health", headers={"host": "evil.example"}).status_code == 400


def test_websocket_rejects_untrusted_origin(client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            "/api/events", headers={"origin": "https://evil.example"}
        ):
            pass


def test_ephemeral_thread_creation_uses_public_app_server_shape(
    client: TestClient, monkeypatch
) -> None:
    codex = client.app.state.codex
    request = AsyncMock(return_value={"thread": {"id": "thread-ephemeral"}})
    monkeypatch.setattr(codex, "request", request)
    monkeypatch.setattr(type(codex), "available", PropertyMock(return_value=True))

    response = client.post(
        "/api/threads",
        json={"cwd": ".", "sandbox": "read-only", "ephemeral": True},
    )

    assert response.status_code == 201
    request.assert_awaited_once_with(
        "thread/start",
        {
            "cwd": str(client.app.state.settings.workspace_root),
            "approvalPolicy": "on-request",
            "sandbox": "read-only",
            "ephemeral": True,
        },
    )


def test_thread_name_forwards_public_app_server_shape(
    client: TestClient, monkeypatch
) -> None:
    codex = client.app.state.codex
    request = AsyncMock(return_value={})
    monkeypatch.setattr(codex, "request", request)
    monkeypatch.setattr(type(codex), "available", PropertyMock(return_value=True))

    response = client.patch(
        "/api/threads/thread-1/name", json={"name": "Markdown rendering"}
    )

    assert response.status_code == 200
    assert response.json() == {}
    request.assert_awaited_once_with(
        "thread/name/set", {"threadId": "thread-1", "name": "Markdown rendering"}
    )


def test_realtime_webrtc_routes_forward_generated_schema(
    client: TestClient, monkeypatch
) -> None:
    codex = client.app.state.codex
    request = AsyncMock(side_effect=[{"voices": {"v1": [], "v2": []}}, {}, {}])
    monkeypatch.setattr(codex, "request", request)
    monkeypatch.setattr(type(codex), "available", PropertyMock(return_value=True))

    assert client.get("/api/realtime/voices").status_code == 200
    started = client.post(
        "/api/threads/thread-voice/realtime/start",
        json={
            "sdp": "v=0\r\no=browser-offer",
            "voice": "marin",
            "version": "v3",
            "include_startup_context": False,
        },
    )
    assert started.status_code == 200
    assert client.post("/api/threads/thread-voice/realtime/stop").status_code == 200
    assert request.await_args_list[0].args == ("thread/realtime/listVoices", {})
    assert request.await_args_list[1].args == (
        "thread/realtime/start",
        {
            "threadId": "thread-voice",
            "outputModality": "audio",
            "transport": {"type": "webrtc", "sdp": "v=0\r\no=browser-offer"},
            "voice": "marin",
            "version": "v3",
            "includeStartupContext": False,
        },
    )
    assert request.await_args_list[2].args == (
        "thread/realtime/stop",
        {"threadId": "thread-voice"},
    )


def test_realtime_webrtc_rejects_v2(client: TestClient) -> None:
    response = client.post(
        "/api/threads/thread-voice/realtime/start",
        json={"sdp": "v=0", "version": "v2"},
    )
    assert response.status_code == 422


def test_realtime_capability_is_gated_by_live_feature_state(
    client: TestClient, monkeypatch
) -> None:
    codex = client.app.state.codex
    request = AsyncMock(return_value={"data": [{"name": "realtime_conversation", "enabled": False}]})
    monkeypatch.setattr(codex, "request", request)
    monkeypatch.setattr(type(codex), "available", PropertyMock(return_value=True))

    response = client.get("/api/threads/thread-voice/realtime/capability")

    assert response.status_code == 200
    assert response.json()["available"] is False
    assert "disabled" in response.json()["reason"]
    request.assert_awaited_once_with(
        "experimentalFeature/list", {"limit": 100, "threadId": "thread-voice"}
    )


def test_realtime_capability_accepts_chatgpt_auth_and_voices(
    client: TestClient, monkeypatch
) -> None:
    codex = client.app.state.codex
    request = AsyncMock(side_effect=[
        {"data": [{"name": "realtime_conversation", "enabled": True}]},
        {"account": {"type": "chatgpt"}, "requiresOpenaiAuth": True},
        {"voices": {"v1": ["cove"], "v2": []}},
    ])
    monkeypatch.setattr(codex, "request", request)
    monkeypatch.setattr(type(codex), "available", PropertyMock(return_value=True))

    response = client.get("/api/threads/thread-voice/realtime/capability")

    assert response.status_code == 200
    assert response.json() == {"available": True}


def test_realtime_capability_requires_account_when_provider_requires_auth(
    client: TestClient, monkeypatch
) -> None:
    codex = client.app.state.codex
    request = AsyncMock(side_effect=[
        {"data": [{"name": "realtime_conversation", "enabled": True}]},
        {"account": None, "requiresOpenaiAuth": True},
    ])
    monkeypatch.setattr(codex, "request", request)
    monkeypatch.setattr(type(codex), "available", PropertyMock(return_value=True))

    response = client.get("/api/threads/thread-voice/realtime/capability")

    assert response.status_code == 200
    assert response.json()["available"] is False
    assert "signed-in Codex account" in response.json()["reason"]
    assert request.await_count == 2


def test_realtime_auth_rejection_does_not_claim_api_key_is_required(
    client: TestClient, monkeypatch
) -> None:
    codex = client.app.state.codex
    request = AsyncMock(side_effect=CodexRPCError({
        "code": -32600,
        "message": "realtime conversation requires API key auth",
    }))
    monkeypatch.setattr(codex, "request", request)
    monkeypatch.setattr(type(codex), "available", PropertyMock(return_value=True))

    response = client.post(
        "/api/threads/thread-voice/realtime/start",
        json={"sdp": "v=0\r\no=browser-offer", "version": "v3"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Codex rejected realtime authentication for this conversation."
    }
    assert "API-key" not in response.text


def test_realtime_protocol_rejection_is_not_exposed_as_bad_gateway(
    client: TestClient, monkeypatch
) -> None:
    codex = client.app.state.codex
    request = AsyncMock(side_effect=CodexRPCError({
        "code": -32600,
        "message": "thread thread-voice does not support realtime conversation",
    }))
    monkeypatch.setattr(codex, "request", request)
    monkeypatch.setattr(type(codex), "available", PropertyMock(return_value=True))

    response = client.post(
        "/api/threads/thread-voice/realtime/start",
        json={"sdp": "v=0\r\no=browser-offer", "version": "v3"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Realtime voice is not enabled for this Codex conversation."}
    assert "rpc_error" not in response.json()
