#!/usr/bin/env python3
"""Read-only realtime capability probe for the installed Codex App Server."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import shutil
import sys
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


def realtime_feature(result: Any) -> dict[str, Any] | None:
    entries = result.get("data", []) if isinstance(result, dict) else []
    return next(
        (
            entry
            for entry in entries
            if isinstance(entry, dict) and entry.get("name") == "realtime_conversation"
        ),
        None,
    )


async def run(codex_executable: str) -> None:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    config_path = codex_home / "config.toml"
    config_before = file_digest(config_path)
    client = CodexAppServerClient(
        [codex_executable, "--enable", "realtime_conversation", "app-server"],
        experimental_api=True,
    )
    if not await client.start():
        raise RuntimeError(client.last_error or "Codex App Server did not start")

    try:
        account_result = await client.request("account/read", {"refreshToken": False})
        feature = realtime_feature(
            await client.request("experimentalFeature/list", {"limit": 100})
        )
        voices_result = await client.request("thread/realtime/listVoices", {})

        account = account_result.get("account") if isinstance(account_result, dict) else None
        requires_auth = (
            account_result.get("requiresOpenaiAuth")
            if isinstance(account_result, dict)
            else None
        )
        if requires_auth is True and not isinstance(account, dict):
            raise RuntimeError("Codex requires a signed-in account but none is available")
        if not isinstance(feature, dict) or feature.get("enabled") is not True:
            raise RuntimeError("realtime_conversation is not enabled in the launched App Server")

        voice_groups = (
            voices_result.get("voices", {}) if isinstance(voices_result, dict) else {}
        )
        v1_count = len(voice_groups.get("v1", [])) if isinstance(voice_groups, dict) else 0
        v2_count = len(voice_groups.get("v2", [])) if isinstance(voice_groups, dict) else 0
        if not (v1_count or v2_count):
            raise RuntimeError("the installed App Server returned no realtime voices")

        account_type = account.get("type", "present") if isinstance(account, dict) else "not-required"
        print(f"PASS App Server version: {client.cli_version or 'unknown'}")
        print(f"PASS account provider: {account_type}")
        print(
            "PASS realtime_conversation is enabled "
            f"(stage={feature.get('stage')}, default={feature.get('defaultEnabled')})"
        )
        print(f"PASS voice discovery returned v1={v1_count}, v2={v2_count}")
        print("PASS no realtime session was started")
    finally:
        await client.stop()

    if file_digest(config_path) != config_before:
        raise RuntimeError("Codex config.toml changed during the capability probe")
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
