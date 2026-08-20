#!/usr/bin/env python3
"""Opt-in live App Server smoke: ephemeral thread plus a denied command approval."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.codex_client import CodexAppServerClient


def file_digest(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def thread_id_from(result: Any) -> str:
    outer = result if isinstance(result, dict) else {}
    thread = outer.get("thread", outer)
    if not isinstance(thread, dict) or not thread.get("id"):
        raise RuntimeError("thread/start did not return thread.id")
    return str(thread["id"])


async def wait_for_approval(
    queue: asyncio.Queue[dict[str, Any]], client: CodexAppServerClient
) -> None:
    while True:
        message = await asyncio.wait_for(queue.get(), timeout=120)
        method = message.get("method")
        if method in {
            "item/commandExecution/requestApproval",
            "item/fileChange/requestApproval",
        }:
            await client.respond_to_server_request(str(message["id"]), {"decision": "decline"})
            return
        if method == "turn/completed":
            raise RuntimeError("turn completed before an approval request was received")


async def wait_for_turn_completion(queue: asyncio.Queue[dict[str, Any]]) -> None:
    while True:
        message = await asyncio.wait_for(queue.get(), timeout=120)
        if message.get("method") == "turn/completed":
            return


async def run(codex_executable: str) -> None:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    config_path = codex_home / "config.toml"
    config_before = file_digest(config_path)
    client = CodexAppServerClient([codex_executable, "app-server"], experimental_api=True)
    if not await client.start():
        raise RuntimeError(client.last_error or "Codex App Server did not start")

    try:
        with tempfile.TemporaryDirectory(prefix="codex-webui-smoke-") as directory:
            workspace = Path(directory)
            marker = workspace / "approval-should-not-run"
            async with client.subscribe() as queue:
                result = await client.request(
                    "thread/start",
                    {
                        "cwd": str(workspace),
                        "approvalPolicy": "on-request",
                        "sandbox": "read-only",
                        "ephemeral": True,
                    },
                )
                thread_id = thread_id_from(result)
                print("PASS thread/start returned an ephemeral thread")
                await client.request(
                    "turn/start",
                    {
                        "threadId": thread_id,
                        "approvalPolicy": "on-request",
                        "sandboxPolicy": {
                            "type": "readOnly",
                            "networkAccess": False,
                        },
                        "input": [
                            {
                                "type": "text",
                                "text": (
                                    "Request approval to run exactly `touch approval-should-not-run` "
                                    "in the current directory. Do not use another tool or modify a file."
                                ),
                            }
                        ],
                    },
                )
                await wait_for_approval(queue, client)
                print("PASS denied one App Server approval request")
                await wait_for_turn_completion(queue)
                if marker.exists():
                    raise RuntimeError("the denied command unexpectedly created its marker")
                print("PASS denied command made no workspace change")
    finally:
        await client.stop()

    if file_digest(config_path) != config_before:
        raise RuntimeError("Codex config.toml changed during the smoke test")
    print("PASS Codex config.toml digest is unchanged")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex-bin", default=os.environ.get("CODEX_BIN") or shutil.which("codex"))
    args = parser.parse_args()
    if not args.codex_bin:
        parser.error("Codex CLI was not found; pass --codex-bin")
    asyncio.run(run(args.codex_bin))


if __name__ == "__main__":
    main()
