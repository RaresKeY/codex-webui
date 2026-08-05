from __future__ import annotations

import asyncio
import contextlib
import mimetypes
import os
import re
import shutil
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .codex_client import CodexAppServerClient, CodexRPCError, CodexUnavailable
from .config import Settings, load_settings, sandbox_policy
from .database import Database
from .models import (
    ApprovalResponse,
    ChatMetadataUpdate,
    FileWrite,
    ProjectCreate,
    ProjectUpdate,
    ScheduledTaskCreate,
    ScheduledTaskUpdate,
    SettingValue,
    ThreadName,
    ThreadResume,
    ThreadStart,
    TurnStart,
    TurnSteer,
)
from .scheduler import TaskScheduler
from .updater import Updater
from .workspace import UnsafePath, Workspace


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    db = Database(settings.database_path)
    codex = CodexAppServerClient(
        settings.codex_argv,
        enabled=settings.codex_enabled,
        line_limit=settings.max_protocol_line_bytes,
    )
    workspace = Workspace(settings.workspace_root, settings.max_file_bytes)
    scheduler = TaskScheduler(
        db, codex, workspace, settings.approval_policy, settings.sandbox
    )
    updater = Updater(settings.update_command, settings.workspace_root)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        settings.image_dir.mkdir(parents=True, exist_ok=True)
        settings.workspace_root.mkdir(parents=True, exist_ok=True)
        await db.initialize()
        await codex.start()  # Failure is intentionally non-fatal: the UI remains usable.
        await scheduler.start()
        yield
        await scheduler.stop()
        await codex.stop()

    app = FastAPI(title="Codex WebUI API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.db = db
    app.state.codex = codex
    app.state.workspace = workspace
    app.state.scheduler = scheduler
    app.state.updater = updater
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

    @app.middleware("http")
    async def reject_cross_site_mutations(request: Request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if request.headers.get("sec-fetch-site") == "cross-site" or not origin_is_allowed(
                origin, request.headers.get("host", ""), settings.allowed_origins
            ):
                from fastapi.responses import JSONResponse

                response = JSONResponse(
                    status_code=403, content={"detail": "Cross-site request rejected"}
                )
                return add_security_headers(response)
        response = await call_next(request)
        return add_security_headers(response)

    @app.exception_handler(CodexUnavailable)
    async def codex_unavailable(_: Request, exc: CodexUnavailable):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=503,
            content={"detail": str(exc), "codex_available": False, "degraded": True},
        )

    @app.exception_handler(CodexRPCError)
    async def codex_error(_: Request, exc: CodexRPCError):
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=502, content={"detail": str(exc), "rpc_error": exc.error})

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok" if codex.available else "degraded",
            "codex_available": codex.available,
            "codex_error": codex.last_error,
            "database": "ok",
        }

    @app.get("/api/system")
    async def system_status() -> dict[str, Any]:
        disk = shutil.disk_usage(settings.workspace_root)
        return {
            "platform": sys.platform,
            "python": sys.version.split()[0],
            "codex": {
                "available": codex.available,
                "command": settings.codex_argv[0] if settings.codex_argv else None,
                "installed": bool(settings.codex_argv and shutil.which(settings.codex_argv[0])),
                "server_info": codex.server_info,
                "error": codex.last_error,
                "approval_policy": settings.approval_policy,
                "sandbox": settings.sandbox,
            },
            "workspace": str(settings.workspace_root),
            "disk": {"total": disk.total, "used": disk.used, "free": disk.free},
        }

    @app.get("/api/bootstrap")
    async def bootstrap() -> dict[str, Any]:
        """One round-trip for initial UI state, including degraded mode."""
        threads, models_result, usage_result = await asyncio.gather(
            list_threads(limit=25), models(), usage()
        )
        return {
            "health": await health(),
            "system": await system_status(),
            "projects": await db.projects(),
            "settings": await db.settings(),
            "tasks": await db.tasks(),
            "threads": threads,
            "models": models_result,
            "usage": usage_result,
            "workspace": workspace.tree(".", depth=1),
            "images": await list_images(),
            "features": {
                "projects": True, "schedules": True, "images": True,
                "workspaceWrite": True, "updates": bool(settings.update_command),
            },
        }

    @app.get("/api/threads")
    async def list_threads(
        q: str | None = None,
        archived: bool = False,
        limit: int = Query(default=50, ge=1, le=200),
        cursor: str | None = None,
    ) -> dict[str, Any]:
        if not codex.available:
            return {"data": [], "nextCursor": None, "degraded": True, "error": codex.last_error}
        params: dict[str, Any] = {
            "limit": limit,
            "archived": archived,
            "sortKey": "recency_at",
            "sortDirection": "desc",
        }
        if q:
            params["searchTerm"] = q
        if cursor:
            params["cursor"] = cursor
        result = await codex.request("thread/list", params)
        response = result if isinstance(result, dict) else {"data": result or []}
        threads = response.get("data", response.get("threads", []))
        metadata = await db.all_chat_metadata()
        enriched = []
        for thread in threads:
            item = dict(thread)
            thread_id = str(item.get("id") or item.get("threadId") or "")
            item["webui"] = metadata.get(thread_id, {"pinned": 0, "project_id": None})
            haystack = " ".join(str(item.get(key, "")) for key in ("name", "title", "preview", "cwd"))
            if not q or q.casefold() in haystack.casefold():
                enriched.append(item)
        response["data"] = sorted(enriched, key=lambda x: not bool(x["webui"].get("pinned")))
        return response

    @app.get("/api/threads/{thread_id}")
    async def read_thread(thread_id: str) -> Any:
        return await codex.request("thread/read", {"threadId": thread_id, "includeTurns": True})

    @app.post("/api/threads", status_code=201)
    async def start_thread(body: ThreadStart) -> Any:
        params: dict[str, Any] = {
            "cwd": str(workspace.resolve(body.cwd or ".", must_exist=True)),
            "approvalPolicy": body.approval_policy or settings.approval_policy,
            "sandbox": body.sandbox or settings.sandbox,
        }
        if body.model:
            params["model"] = body.model
        result = await codex.request("thread/start", params)
        if body.prompt:
            thread = result.get("thread", result) if isinstance(result, dict) else {}
            thread_id = thread.get("id") or thread.get("threadId")
            if not thread_id:
                raise HTTPException(502, "Codex did not return a thread id")
            turn = await codex.request(
                "turn/start",
                {"threadId": thread_id, "input": [{"type": "text", "text": body.prompt}]},
            )
            return {"thread": result, "turn": turn}
        return result

    @app.post("/api/threads/{thread_id}/resume")
    async def resume_thread(thread_id: str, body: ThreadResume) -> Any:
        params: dict[str, Any] = {"threadId": thread_id}
        if body.cwd:
            params["cwd"] = str(workspace.resolve(body.cwd, must_exist=True))
        if body.model:
            params["model"] = body.model
        return await codex.request("thread/resume", params)

    @app.patch("/api/threads/{thread_id}/name")
    async def name_thread(thread_id: str, body: ThreadName) -> Any:
        return await codex.request("thread/name/set", {"threadId": thread_id, "name": body.name})

    @app.post("/api/threads/{thread_id}/archive")
    async def archive_thread(thread_id: str) -> Any:
        return await codex.request("thread/archive", {"threadId": thread_id})

    @app.post("/api/threads/{thread_id}/fork", status_code=201)
    async def fork_thread(thread_id: str) -> Any:
        return await codex.request("thread/fork", {"threadId": thread_id})

    @app.patch("/api/threads/{thread_id}/metadata")
    async def set_thread_metadata(thread_id: str, body: ChatMetadataUpdate) -> dict[str, Any]:
        existing = await db.fetchone(
            "SELECT project_id,pinned FROM chat_metadata WHERE thread_id=?", (thread_id,)
        ) or {"project_id": None, "pinned": 0}
        project_id = (
            body.project_id if "project_id" in body.model_fields_set else existing["project_id"]
        )
        pinned = body.pinned if "pinned" in body.model_fields_set else bool(existing["pinned"])
        if project_id is not None and not await db.fetchone(
            "SELECT id FROM projects WHERE id=?", (project_id,)
        ):
            raise HTTPException(404, "Project not found")
        return await db.set_chat_metadata(thread_id, project_id, bool(pinned))

    @app.post("/api/threads/{thread_id}/pin")
    async def pin_thread(thread_id: str) -> dict[str, Any]:
        existing = await db.fetchone(
            "SELECT project_id FROM chat_metadata WHERE thread_id=?", (thread_id,)
        ) or {"project_id": None}
        return await db.set_chat_metadata(thread_id, existing["project_id"], True)

    @app.delete("/api/threads/{thread_id}/pin")
    async def unpin_thread(thread_id: str) -> dict[str, Any]:
        existing = await db.fetchone(
            "SELECT project_id FROM chat_metadata WHERE thread_id=?", (thread_id,)
        ) or {"project_id": None}
        return await db.set_chat_metadata(thread_id, existing["project_id"], False)

    @app.post("/api/threads/{thread_id}/turns", status_code=201)
    async def start_turn(thread_id: str, body: TurnStart) -> Any:
        params: dict[str, Any] = {
            "threadId": thread_id,
            "input": [{"type": "text", "text": body.input}],
            "approvalPolicy": body.approval_policy or settings.approval_policy,
        }
        if body.sandbox:
            params["sandboxPolicy"] = sandbox_policy(body.sandbox, settings.workspace_root)
        if body.model:
            params["model"] = body.model
        if body.effort:
            params["effort"] = body.effort
        return await codex.request("turn/start", params)

    @app.post("/api/threads/{thread_id}/turns/{turn_id}/steer")
    async def steer_turn(thread_id: str, turn_id: str, body: TurnSteer) -> Any:
        params: dict[str, Any] = {
            "threadId": thread_id,
            "expectedTurnId": body.expected_turn_id or turn_id,
            "input": [{"type": "text", "text": body.input}],
        }
        return await codex.request("turn/steer", params)

    @app.post("/api/threads/{thread_id}/turns/{turn_id}/interrupt")
    async def interrupt_turn(thread_id: str, turn_id: str) -> Any:
        return await codex.request("turn/interrupt", {"threadId": thread_id, "turnId": turn_id})

    @app.websocket("/api/events")
    async def events(websocket: WebSocket) -> None:
        if not websocket_origin_is_allowed(websocket, settings.allowed_origins):
            await websocket.close(code=1008, reason="Origin is not allowed")
            return
        await websocket.accept()
        try:
            await websocket.send_json(
                {"method": "webui/status", "params": {"codexAvailable": codex.available, "error": codex.last_error}}
            )
            async with codex.subscribe() as queue:
                while True:
                    await websocket.send_json(await queue.get())
        except (WebSocketDisconnect, RuntimeError):
            return

    @app.get("/api/approvals")
    async def approvals() -> dict[str, Any]:
        return {"data": codex.pending_server_requests()}

    @app.post("/api/approvals/{request_id}")
    async def resolve_approval(request_id: str, body: ApprovalResponse) -> dict[str, bool]:
        try:
            await codex.respond_to_server_request(request_id, body.response)
        except KeyError:
            raise HTTPException(404, "Approval request not found") from None
        return {"ok": True}

    @app.post("/api/approvals/{request_id}/reject")
    async def reject_unsupported_request(request_id: str) -> dict[str, bool]:
        try:
            await codex.reject_server_request(request_id)
        except KeyError:
            raise HTTPException(404, "App Server request not found") from None
        return {"ok": True}

    @app.get("/api/account")
    async def account() -> Any:
        if not codex.available:
            return {"available": False, "degraded": True, "error": codex.last_error}
        return await codex.request("account/read", {})

    @app.get("/api/usage")
    async def usage() -> Any:
        if not codex.available:
            return {"available": False, "rateLimits": None, "usage": None, "degraded": True}

        async def optional(method: str) -> dict[str, Any]:
            try:
                return {"data": await codex.request(method, {}), "error": None}
            except (CodexRPCError, CodexUnavailable) as exc:
                return {"data": None, "error": str(exc)}

        rate_limits, account_usage = await asyncio.gather(
            optional("account/rateLimits/read"), optional("account/usage/read")
        )
        return {
            "available": bool(rate_limits["data"] is not None or account_usage["data"] is not None),
            "rateLimits": rate_limits["data"],
            "usage": account_usage["data"],
            "errors": {
                key: value for key, value in (
                    ("rateLimits", rate_limits["error"]), ("usage", account_usage["error"])
                ) if value
            },
        }

    @app.get("/api/models")
    async def models() -> Any:
        if not codex.available:
            return {"data": [], "degraded": True, "error": codex.last_error}
        result = await codex.request("model/list", {})
        return result if isinstance(result, dict) else {"data": result or []}

    @app.get("/api/workspace/tree")
    async def workspace_tree(path: str = ".", depth: int = Query(2, ge=0, le=5)) -> Any:
        try:
            return workspace.tree(path, depth)
        except UnsafePath as exc:
            raise HTTPException(403, str(exc)) from None
        except FileNotFoundError:
            raise HTTPException(404, "Path not found") from None
        except (NotADirectoryError, PermissionError) as exc:
            raise HTTPException(400, str(exc)) from None

    @app.get("/api/workspace/file")
    async def read_workspace_file(path: str) -> Any:
        try:
            return workspace.read(path)
        except UnsafePath as exc:
            raise HTTPException(403, str(exc)) from None
        except FileNotFoundError:
            raise HTTPException(404, "File not found") from None
        except (ValueError, IsADirectoryError, PermissionError) as exc:
            raise HTTPException(400, str(exc)) from None

    @app.put("/api/workspace/file")
    async def write_workspace_file(path: str, body: FileWrite) -> Any:
        try:
            return workspace.write(path, body.content)
        except UnsafePath as exc:
            raise HTTPException(403, str(exc)) from None
        except (ValueError, OSError, PermissionError) as exc:
            raise HTTPException(400, str(exc)) from None

    @app.get("/api/images")
    async def list_images() -> dict[str, Any]:
        data = []
        for path in sorted(settings.image_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if path.is_file():
                stat = path.stat()
                data.append({
                    "id": path.name, "name": path.name, "size": stat.st_size,
                    "mime": mimetypes.guess_type(path.name)[0], "modified_at": stat.st_mtime,
                    "url": f"/api/images/{path.name}",
                })
        return {"data": data}

    @app.get("/api/images/{image_id}")
    async def get_image(image_id: str):
        from fastapi.responses import FileResponse

        path = safe_image_path(settings.image_dir, image_id)
        if not path.is_file():
            raise HTTPException(404, "Image not found")
        return FileResponse(path)

    @app.post("/api/images", status_code=201)
    async def upload_image(file: UploadFile = File(...)) -> dict[str, Any]:
        data = await file.read(settings.max_image_bytes + 1)
        if len(data) > settings.max_image_bytes:
            raise HTTPException(413, "Image exceeds upload limit")
        suffix, mime = detect_image(data)
        if not suffix:
            raise HTTPException(415, "Only PNG, JPEG, GIF, and WebP images are accepted")
        name = f"{uuid.uuid4().hex}{suffix}"
        path = safe_image_path(settings.image_dir, name)
        path.write_bytes(data)
        return {"id": name, "name": file.filename or name, "size": len(data), "mime": mime, "url": f"/api/images/{name}"}

    @app.delete("/api/images/{image_id}", status_code=204)
    async def delete_image(image_id: str) -> None:
        path = safe_image_path(settings.image_dir, image_id)
        if not path.is_file():
            raise HTTPException(404, "Image not found")
        path.unlink()

    @app.get("/api/projects")
    async def projects() -> dict[str, Any]:
        return {"data": await db.projects()}

    @app.post("/api/projects", status_code=201)
    async def create_project(body: ProjectCreate) -> Any:
        data = body.model_dump()
        try:
            project_workspace = workspace.resolve(body.workspace, must_exist=True)
        except (UnsafePath, FileNotFoundError) as exc:
            raise HTTPException(400, str(exc)) from None
        if not project_workspace.is_dir():
            raise HTTPException(400, "Project workspace must be a directory")
        data["workspace"] = str(project_workspace.relative_to(settings.workspace_root))
        return await db.create_project(data)

    @app.patch("/api/projects/{project_id}")
    async def update_project(project_id: int, body: ProjectUpdate) -> Any:
        data = body.model_dump(exclude_unset=True)
        if "workspace" in data and data["workspace"] is not None:
            try:
                project_workspace = workspace.resolve(data["workspace"], must_exist=True)
            except (UnsafePath, FileNotFoundError) as exc:
                raise HTTPException(400, str(exc)) from None
            if not project_workspace.is_dir():
                raise HTTPException(400, "Project workspace must be a directory")
            data["workspace"] = str(project_workspace.relative_to(settings.workspace_root))
        result = await db.update_project(project_id, data)
        if not result:
            raise HTTPException(404, "Project not found")
        return result

    @app.delete("/api/projects/{project_id}", status_code=204)
    async def delete_project(project_id: int) -> None:
        if not await db.fetchone("SELECT id FROM projects WHERE id=?", (project_id,)):
            raise HTTPException(404, "Project not found")
        await db.execute("DELETE FROM projects WHERE id=?", (project_id,))

    @app.get("/api/settings")
    async def all_settings() -> dict[str, Any]:
        return await db.settings()

    @app.put("/api/settings/{key}")
    async def set_setting(key: str, body: SettingValue) -> dict[str, Any]:
        if not re.fullmatch(r"[a-zA-Z0-9_.-]{1,100}", key):
            raise HTTPException(400, "Invalid setting key")
        await db.set_setting(key, body.value)
        return {"key": key, "value": body.value}

    @app.get("/api/tasks")
    async def tasks() -> dict[str, Any]:
        return {"data": await db.tasks()}

    @app.post("/api/tasks", status_code=201)
    async def create_task(body: ScheduledTaskCreate) -> Any:
        try:
            TaskScheduler._trigger(body.schedule_type, body.schedule)
            workspace.resolve(body.workspace, must_exist=True)
        except (ValueError, FileNotFoundError, UnsafePath) as exc:
            raise HTTPException(400, str(exc)) from None
        result = await db.create_task(body.model_dump())
        scheduler.refresh(result)
        return result

    @app.patch("/api/tasks/{task_id}")
    async def update_task(task_id: int, body: ScheduledTaskUpdate) -> Any:
        current = await db.task(task_id)
        if not current:
            raise HTTPException(404, "Task not found")
        merged = current | body.model_dump(exclude_unset=True)
        try:
            TaskScheduler._trigger(merged["schedule_type"], merged["schedule"])
            workspace.resolve(merged["workspace"], must_exist=True)
        except (ValueError, FileNotFoundError, UnsafePath) as exc:
            raise HTTPException(400, str(exc)) from None
        result = await db.update_task(task_id, body.model_dump(exclude_unset=True))
        assert result
        scheduler.refresh(result)
        return result

    @app.delete("/api/tasks/{task_id}", status_code=204)
    async def delete_task(task_id: int) -> None:
        if not await db.task(task_id):
            raise HTTPException(404, "Task not found")
        scheduler.unschedule(task_id)
        await db.execute("DELETE FROM scheduled_tasks WHERE id=?", (task_id,))

    @app.post("/api/tasks/{task_id}/run", status_code=202)
    async def run_task(task_id: int) -> dict[str, bool]:
        if not await db.task(task_id):
            raise HTTPException(404, "Task not found")
        if not scheduler.launch_task(task_id):
            raise HTTPException(409, "Task is already running")
        return {"accepted": True}

    @app.get("/api/update")
    async def update_status() -> Any:
        return updater.status()

    @app.post("/api/update", status_code=202)
    async def request_update() -> Any:
        try:
            return updater.request()
        except ValueError as exc:
            raise HTTPException(403, str(exc)) from None
        except RuntimeError as exc:
            raise HTTPException(409, str(exc)) from None

    # Compatibility surface for the first-party frontend vocabulary. The
    # canonical API uses Codex's "thread" terminology; both paths are stable.
    @app.get("/api/conversations", include_in_schema=False)
    async def conversations_alias(
        q: str | None = None,
        archived: bool = False,
        limit: int = Query(default=50, ge=1, le=200),
        cursor: str | None = None,
    ) -> Any:
        return await list_threads(q=q, archived=archived, limit=limit, cursor=cursor)

    @app.post("/api/conversations", status_code=201, include_in_schema=False)
    async def create_conversation_alias(body: ThreadStart) -> Any:
        return await start_thread(body)

    @app.get("/api/conversations/{thread_id}", include_in_schema=False)
    async def read_conversation_alias(thread_id: str) -> Any:
        return await read_thread(thread_id)

    @app.post("/api/conversations/{thread_id}/resume", include_in_schema=False)
    async def resume_conversation_alias(thread_id: str, body: ThreadResume) -> Any:
        return await resume_thread(thread_id, body)

    @app.patch("/api/conversations/{thread_id}/name", include_in_schema=False)
    async def name_conversation_alias(thread_id: str, body: ThreadName) -> Any:
        return await name_thread(thread_id, body)

    @app.delete("/api/conversations/{thread_id}", include_in_schema=False)
    async def archive_conversation_alias(thread_id: str) -> Any:
        return await archive_thread(thread_id)

    @app.post("/api/conversations/{thread_id}/fork", status_code=201, include_in_schema=False)
    async def fork_conversation_alias(thread_id: str) -> Any:
        return await fork_thread(thread_id)

    @app.post("/api/conversations/{thread_id}/turns", status_code=201, include_in_schema=False)
    async def conversation_turn_alias(thread_id: str, body: TurnStart) -> Any:
        return await start_turn(thread_id, body)

    @app.post(
        "/api/conversations/{thread_id}/turns/{turn_id}/interrupt", include_in_schema=False
    )
    async def conversation_interrupt_alias(thread_id: str, turn_id: str) -> Any:
        return await interrupt_turn(thread_id, turn_id)

    @app.get("/api/system/update", include_in_schema=False)
    async def system_update_status_alias() -> Any:
        return updater.status()

    @app.post("/api/system/update", status_code=202, include_in_schema=False)
    async def system_update_alias() -> Any:
        return await request_update()

    @app.websocket("/ws/conversations/{thread_id}")
    async def conversation_events_alias(websocket: WebSocket, thread_id: str) -> None:
        if not websocket_origin_is_allowed(websocket, settings.allowed_origins):
            await websocket.close(code=1008, reason="Origin is not allowed")
            return
        await websocket.accept()
        try:
            await websocket.send_json(
                {"method": "webui/status", "params": {"codexAvailable": codex.available, "threadId": thread_id}}
            )
            async with codex.subscribe() as queue:
                while True:
                    message = await queue.get()
                    if event_is_for_thread(message, thread_id):
                        await websocket.send_json(message)
        except (WebSocketDisconnect, RuntimeError):
            return

    frontend_dist = settings.frontend_dist
    if frontend_dist and frontend_dist.is_dir() and (frontend_dist / "index.html").is_file():
        assets = frontend_dist / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="frontend-assets")

        @app.get("/{spa_path:path}", include_in_schema=False)
        async def spa_fallback(spa_path: str):
            from fastapi.responses import FileResponse

            if spa_path.startswith("api/"):
                raise HTTPException(404, "API route not found")
            candidate = (frontend_dist / spa_path).resolve()
            with contextlib.suppress(ValueError):
                candidate.relative_to(frontend_dist)
                if candidate.is_file():
                    return FileResponse(candidate)
            return FileResponse(frontend_dist / "index.html")
    else:
        @app.get("/", include_in_schema=False)
        async def no_frontend_root() -> dict[str, Any]:
            return {
                "name": "Codex WebUI API",
                "status": "frontend-not-built",
                "docs": "/docs",
            }

    return app


def safe_image_path(root: Path, image_id: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{32}\.(png|jpg|gif|webp)", image_id):
        raise HTTPException(400, "Invalid image id")
    path = (root / image_id).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        raise HTTPException(400, "Invalid image id") from None
    return path


def detect_image(data: bytes) -> tuple[str | None, str | None]:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg", "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return ".gif", "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp", "image/webp"
    return None, None


def event_thread_id(message: dict[str, Any]) -> str | None:
    """Extract the owning thread from known App Server event envelopes."""
    params = message.get("params")
    if not isinstance(params, dict):
        return None
    direct = params.get("threadId") or params.get("thread_id")
    if direct is not None:
        return str(direct)
    for key in ("thread", "turn", "item"):
        value = params.get(key)
        if isinstance(value, dict):
            nested = value.get("threadId") or value.get("thread_id")
            if nested is not None:
                return str(nested)
            if key == "thread" and value.get("id") is not None:
                return str(value["id"])
    return None


def event_is_for_thread(message: dict[str, Any], thread_id: str) -> bool:
    """Keep conversation sockets isolated while retaining explicit globals."""
    scoped_thread = event_thread_id(message)
    if scoped_thread is not None:
        return scoped_thread == thread_id
    method = message.get("method")
    return isinstance(method, str) and method.startswith(("webui/", "account/"))


def add_security_headers(response: Any) -> Any:
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; "
        "script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; connect-src 'self' ws: wss:",
    )
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


def origin_is_allowed(origin: str | None, host: str, allowed_origins: list[str]) -> bool:
    """Allow non-browser clients, configured dev origins, and the exact same origin."""
    if not origin:
        return True
    normalized = origin.rstrip("/")
    if normalized in {item.rstrip("/") for item in allowed_origins}:
        return True
    parsed = urlsplit(normalized)
    return parsed.scheme in {"http", "https"} and parsed.netloc.casefold() == host.casefold()


def websocket_origin_is_allowed(websocket: WebSocket, allowed_origins: list[str]) -> bool:
    return origin_is_allowed(
        websocket.headers.get("origin"), websocket.headers.get("host", ""), allowed_origins
    )


app = create_app()
