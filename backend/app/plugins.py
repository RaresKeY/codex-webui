"""Read installed plugin metadata and resolve explicit composer mentions."""
from __future__ import annotations

import re
from typing import Any

from .codex_client import CodexAppServerClient, CodexRPCError
from .workspace import UnsafePath, Workspace


class PluginError(RuntimeError):
    pass


class PluginCatalog:
    def __init__(self, codex: CodexAppServerClient, workspace: Workspace):
        self.codex, self.workspace = codex, workspace

    async def entries(self, cwd: str) -> list[dict[str, str]]:
        try:
            resolved = self.workspace.resolve(cwd, must_exist=True)
            if not resolved.is_dir():
                raise ValueError()
            root = str(resolved)
        except (UnsafePath, OSError, ValueError):
            raise PluginError("The plugin workspace is unavailable.") from None
        try:
            result = await self.codex.request("plugin/installed", {"cwds": [root]})
        except CodexRPCError:
            raise PluginError("The installed Codex could not list plugins for this workspace.") from None
        if not isinstance(result, dict) or not isinstance(result.get("marketplaces"), list):
            raise PluginError("Codex returned an invalid plugin catalog.")
        entries: dict[str, dict[str, str]] = {}
        for marketplace in result["marketplaces"]:
            if not isinstance(marketplace, dict):
                continue
            plugins = marketplace.get("plugins", [])
            if not isinstance(plugins, list):
                raise PluginError("Codex returned an invalid plugin catalog.")
            for plugin in plugins:
                if not isinstance(plugin, dict) or plugin.get("installed") is not True or plugin.get("enabled") is not True:
                    continue
                if plugin.get("availability") not in (None, "AVAILABLE"):
                    continue
                identifier, name = plugin.get("id"), plugin.get("name")
                if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9._-]+@[A-Za-z0-9._-]+", identifier):
                    continue
                if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", name) or len(identifier) > 256 or identifier.split("@", 1)[0] != name:
                    continue
                interface = plugin.get("interface") or {}
                if not isinstance(interface, dict):
                    interface = {}
                display_name, description = interface.get("displayName"), interface.get("shortDescription")
                entries[identifier] = {
                    "id": identifier, "name": name,
                    "displayName": (display_name if isinstance(display_name, str) and display_name else name)[:160],
                    "description": description[:500] if isinstance(description, str) else "",
                }
        if result.get("marketplaceLoadErrors") and not entries:
            raise PluginError("Installed plugin metadata could not be loaded. Retry after checking Codex.")
        return sorted(entries.values(), key=lambda entry: entry["displayName"].casefold())[:256]

    async def resolve(self, identifiers: list[str], ask: str, cwd: str) -> list[dict[str, Any]]:
        if not identifiers:
            return []
        catalog = {entry["id"]: entry for entry in await self.entries(cwd)}
        mentions = []
        for identifier in identifiers:
            plugin = catalog.get(identifier)
            if plugin is None or not re.search(r"(?<![\w@])@" + re.escape(plugin["name"]) + r"(?![\w.-])", ask):
                raise PluginError("A selected plugin is unavailable or no longer mentioned. Review the message and try again.")
            mentions.append({"type": "mention", "name": plugin["name"], "path": "plugin://" + identifier})
        return mentions
