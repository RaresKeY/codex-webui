from __future__ import annotations

from unittest.mock import AsyncMock, PropertyMock

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import event_is_for_thread, event_thread_id


def test_bootstrap_and_degraded_threads(client: TestClient) -> None:
    bootstrap = client.get("/api/bootstrap")
    assert bootstrap.status_code == 200
    assert bootstrap.json()["health"]["status"] == "degraded"
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
