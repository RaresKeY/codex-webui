"""One server-owned text-chat operation: route, bind, then submit exact input."""
from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any
import sqlite3

from .codex_client import CodexAppServerClient, CodexRPCError, CodexTimeout, CodexUnavailable
from .config import Settings, sandbox_policy
from .models import TurnStart, ChatExecution
from .database import Database
from .mentions import MentionCatalog
from .plugins import PluginCatalog, PluginError
from .permissions import PermissionMode, permission_overrides
from .task_router import EFFORTS, MODELS, RoutingError, TaskRouter

UNSUPPORTED_HISTORY_MESSAGE = (
    "This conversation uses a history mode that the installed Codex cannot resume. "
    "Start a new chat and send your message there. Existing history has not been changed."
)


def unsupported_history(exc: CodexRPCError) -> bool:
    message = exc.error.get("message") if isinstance(exc.error, dict) else None
    return isinstance(message, str) and message.casefold() == "list_turns is not supported yet"


class MessageError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


class RoutedChat:
    def __init__(self, codex: CodexAppServerClient, router: TaskRouter, settings: Settings, plugins: PluginCatalog, mentions: MentionCatalog, db: Database):
        self.codex, self.router, self.settings = codex, router, settings
        self.plugins = plugins
        self.mentions, self.db = mentions, db
        self._sending: set[str] = set()

    @asynccontextmanager
    async def reserve(self, thread_id: str):
        if not self.codex.available:
            raise MessageError(503, "Connect the local Codex service before sending a message.")
        if thread_id in self._sending:
            raise MessageError(409, "A message is already being submitted to this conversation.")
        self._sending.add(thread_id)
        try:
            yield
        finally:
            self._sending.discard(thread_id)

    async def ensure_loaded(self, thread_id: str) -> None:
        loaded = await self.codex.request("thread/loaded/list", {})
        if not isinstance(loaded, dict) or not isinstance(loaded.get("data"), list):
            raise MessageError(502, "Codex could not confirm the loaded conversation.")
        if thread_id not in loaded["data"]:
            await self.codex.request("thread/resume", {"threadId": thread_id, "excludeTurns": True})

    async def bind(self, thread_id: str, overrides: dict[str, Any]) -> None:
        await self.ensure_loaded(thread_id)
        acknowledgement = await self.codex.request("thread/settings/update", {"threadId": thread_id, **overrides})
        if acknowledgement != {}:
            raise MessageError(502, "Codex did not acknowledge the selected model. Your message was not sent.")

    async def permission_mode(self, thread_id: str) -> PermissionMode:
        mode = await self.db.get_setting("chat-permissions:" + thread_id, "default")
        if mode not in {"default", "full-auto", "yolo"}:
            raise MessageError(409, "This chat's saved permissions are invalid. Choose permissions again.")
        return mode

    async def set_permissions(self, thread_id: str, mode: PermissionMode) -> None:
        async with self.reserve(thread_id):
            try:
                metadata = await self.codex.request("thread/read", {"threadId": thread_id, "includeTurns": False})
                thread = metadata.get("thread", {}) if isinstance(metadata, dict) else {}
                if not isinstance(thread, dict) or thread.get("id") != thread_id:
                    raise MessageError(502, "Codex could not confirm this conversation.")
                status = thread.get("status", {})
                if status == "active" or isinstance(status, dict) and status.get("type") == "active":
                    raise MessageError(409, "Wait for the current turn to finish before changing permissions.")
                await self.ensure_loaded(thread_id)
                acknowledgement = await self.codex.request("thread/settings/update", {"threadId": thread_id, **permission_overrides(mode, self.settings)})
                if acknowledgement != {}:
                    raise MessageError(502, "Codex did not acknowledge the permission change.")
                await self.db.set_settings({"chat-permissions:" + thread_id: mode, "new-chat-permissions": mode})
            except CodexRPCError as exc:
                if unsupported_history(exc):
                    raise MessageError(409, UNSUPPORTED_HISTORY_MESSAGE) from None
                raise MessageError(502, "Codex could not apply these permissions. Check the conversation before retrying.") from None
            except sqlite3.Error:
                raise MessageError(503, "Codex updated permissions, but the choice could not be saved. Set permissions again before sending.") from None

    async def execution(self, thread_id: str) -> ChatExecution:
        raw = await self.db.get_setting("chat-execution:" + thread_id, {"model": "auto", "effort": "medium"})
        try:
            return ChatExecution.model_validate(raw)
        except ValueError:
            raise MessageError(409, "This chat's model selection is invalid. Choose a model again.") from None

    async def set_execution(self, thread_id: str, choice: ChatExecution) -> None:
        async with self.reserve(thread_id):
            try:
                metadata = await self.codex.request("thread/read", {"threadId": thread_id, "includeTurns": False})
                thread = metadata.get("thread", {}) if isinstance(metadata, dict) else {}
                if not isinstance(thread, dict) or thread.get("id") != thread_id:
                    raise MessageError(502, "Codex could not confirm this conversation.")
                status = thread.get("status", {})
                if status == "active" or isinstance(status, dict) and status.get("type") == "active":
                    raise MessageError(409, "Wait for the current turn to finish before changing the model.")
                if choice.model != "auto":
                    await self.bind(thread_id, {"model": choice.model, "effort": choice.effort})
                await self.db.set_setting("chat-execution:" + thread_id, choice.model_dump())
            except CodexRPCError as exc:
                if unsupported_history(exc):
                    raise MessageError(409, UNSUPPORTED_HISTORY_MESSAGE) from None
                raise MessageError(502, "Codex could not apply this model selection. Check settings before retrying.") from None
            except sqlite3.Error:
                raise MessageError(503, "The selection could not be saved. Choose the model again before sending.") from None

    async def send(
        self, thread_id: str, body: TurnStart,
        cancelled: Callable[[], Awaitable[bool]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        async def check_cancelled():
            if cancelled and await cancelled():
                raise MessageError(499, "Submission cancelled before the next step.")

        async with self.reserve(thread_id):
            stage = "routing"
            try:
                await check_cancelled()
                yield {"stage": stage}
                metadata = await self.codex.request("thread/read", {"threadId": thread_id, "includeTurns": False})
                thread = metadata.get("thread", {}) if isinstance(metadata, dict) else {}
                if not isinstance(thread, dict) or thread.get("id") != thread_id:
                    raise MessageError(502, "Codex could not confirm this conversation. Your message was not sent.")
                if thread.get("historyMode") == "paginated":
                    raise MessageError(409, UNSUPPORTED_HISTORY_MESSAGE)
                status = thread.get("status", {})
                if status == "active" or isinstance(status, dict) and status.get("type") == "active":
                    raise MessageError(409, "Wait for the current turn to finish before sending another message.")
                permissions = permission_overrides(await self.permission_mode(thread_id), self.settings)
                if body.approval_policy:
                    permissions["approvalPolicy"] = body.approval_policy
                if body.sandbox:
                    permissions["sandboxPolicy"] = sandbox_policy(body.sandbox, self.settings.workspace_root)
                cwd = thread.get("cwd") or str(self.settings.workspace_root)
                mentions = await self.plugins.resolve(body.plugins, body.input, cwd)
                if any(identifier.startswith("app:") for identifier in body.mentions):
                    await self.ensure_loaded(thread_id)
                mentions.extend(await self.mentions.resolve(body.mentions, body.input, cwd, thread_id))
                await check_cancelled()
                choice = await self.execution(thread_id)
                decision = await self.router.choose(body.input) if choice.model == "auto" else {
                    "model": choice.model, "effort": choice.effort, "reviewNeeded": False,
                    "policy": "manual", "source": "manual",
                }
                model, effort = decision.get("model"), decision.get("effort")
                if model not in MODELS or effort not in EFFORTS:
                    raise MessageError(409, "Jev returned an unsupported routing decision. Your message was not sent.")
                if choice.model == "auto" and (decision.get("reviewNeeded") or model == "gpt-6-luna" and effort in {"high", "xhigh", "max"}):
                    raise MessageError(409, "Jev selected Luna with unusually high reasoning. Review the routing policy before sending this message.")
                await check_cancelled()
                stage = "switching"
                yield {"stage": stage, "decision": decision}
                await self.bind(thread_id, {"model": model, "effort": effort, **permissions})
                await check_cancelled()
                await self.codex.publish_model_selection(thread_id, model, effort)
                stage = "sending"
                yield {"stage": stage, "decision": decision}
                await check_cancelled()
                params = {
                    "threadId": thread_id,
                    "input": [{"type": "text", "text": body.input}, *mentions],
                    "model": model, "effort": effort,
                    **permissions,
                }
                result = await self.codex.request("turn/start", params)
                if not isinstance(result, dict) or not isinstance(result.get("turn"), dict) or not result["turn"].get("id"):
                    raise MessageError(502, "Codex could not confirm submission. Check the conversation before retrying.")
                saved = True
                try:
                    await self.db.record_turn_selection(thread_id, result["turn"]["id"], model, effort)
                except sqlite3.Error:
                    # The acknowledged turn has already started. Metadata failure
                    # must never report a failed send or trigger a duplicate retry.
                    saved = False
                yield {"result": {**result, "decision": decision, "modelChangeAcknowledged": True, "selectionSaved": saved}}
            except RoutingError as exc:
                raise MessageError(409, str(exc)) from None
            except PluginError as exc:
                raise MessageError(409, str(exc)) from None
            except CodexTimeout:
                raise MessageError(504, "Codex took too long to respond. Check the conversation before retrying.") from None
            except CodexUnavailable:
                raise MessageError(503, "The local Codex service disconnected. Check the conversation before retrying.") from None
            except CodexRPCError as exc:
                if unsupported_history(exc):
                    raise MessageError(409, UNSUPPORTED_HISTORY_MESSAGE) from None
                message = {
                    "routing": "Codex could not load this conversation. Your message was not sent.",
                    "switching": "Codex could not apply the selected model. Your message was not sent.",
                    "sending": "Codex could not confirm submission. Check the conversation before retrying.",
                }[stage]
                raise MessageError(502, message) from None
