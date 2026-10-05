"""One server-owned text-chat operation: route, bind, then submit exact input."""
from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from .codex_client import CodexAppServerClient, CodexRPCError, CodexUnavailable
from .config import Settings, sandbox_policy
from .models import TurnStart
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
    def __init__(self, codex: CodexAppServerClient, router: TaskRouter, settings: Settings):
        self.codex, self.router, self.settings = codex, router, settings
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
                await check_cancelled()
                decision = await self.router.choose(body.input)
                model, effort = decision.get("model"), decision.get("effort")
                if model not in MODELS or effort not in EFFORTS:
                    raise MessageError(409, "Jev returned an unsupported routing decision. Your message was not sent.")
                if decision.get("reviewNeeded") or model == "gpt-6-luna" and effort in {"high", "xhigh", "max"}:
                    raise MessageError(409, "Jev selected Luna with unusually high reasoning. Review the routing policy before sending this message.")
                await check_cancelled()
                stage = "switching"
                yield {"stage": stage, "decision": decision}
                await self.bind(thread_id, {"model": model, "effort": effort})
                await check_cancelled()
                await self.codex.publish_model_selection(thread_id, model)
                stage = "sending"
                yield {"stage": stage, "decision": decision}
                await check_cancelled()
                params = {
                    "threadId": thread_id,
                    "input": [{"type": "text", "text": body.input}],
                    "model": model, "effort": effort,
                    "approvalPolicy": body.approval_policy or self.settings.approval_policy,
                }
                if body.sandbox:
                    params["sandboxPolicy"] = sandbox_policy(body.sandbox, self.settings.workspace_root)
                result = await self.codex.request("turn/start", params)
                if not isinstance(result, dict) or not isinstance(result.get("turn"), dict) or not result["turn"].get("id"):
                    raise MessageError(502, "Codex could not confirm submission. Check the conversation before retrying.")
                yield {"result": {**result, "decision": decision, "modelChangeAcknowledged": True}}
            except RoutingError as exc:
                raise MessageError(409, str(exc)) from None
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
