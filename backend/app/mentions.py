"""Project native mention catalogs; never accept caller-provided native paths."""
from __future__ import annotations

import asyncio
import hashlib
import re
from pathlib import Path
from urllib.parse import quote, unquote

from .codex_client import CodexAppServerClient, CodexRPCError, CodexUnavailable
from .plugins import PluginCatalog, PluginError
from .workspace import Workspace, UnsafePath


def literal_present(text: str, literal: str) -> bool:
    end = r"(?!\w)" if literal.endswith('"') else r"(?![\w.\-/])"
    return bool(re.search(r"(?<![\w@$])" + re.escape(literal) + end, text))


class MentionCatalog:
    def __init__(self, codex: CodexAppServerClient, workspace: Workspace, plugins: PluginCatalog):
        self.codex, self.workspace, self.plugins = codex, workspace, plugins

    def root(self, cwd: str) -> Path:
        try:
            root = self.workspace.resolve(cwd, must_exist=True)
            if not root.is_dir():
                raise ValueError()
            return root
        except (UnsafePath, OSError, ValueError, RuntimeError):
            raise PluginError("The mention workspace is unavailable.") from None

    async def category(self, kind: str, cwd: str, thread_id: str | None = None, errors: list[dict] | None = None) -> list[dict]:
        root = self.root(cwd)
        entries = []
        if kind == "plugin":
            for plugin in await self.plugins.entries(str(root)):
                entries.append({**plugin, "id": "plugin:" + plugin["id"], "kind": kind,
                                "insertText": "@" + plugin["name"],
                                "native": {"type": "mention", "name": plugin["name"], "path": "plugin://" + plugin["id"]}})
        elif kind == "skill":
            result = await self.codex.request("skills/list", {"cwds": [str(root)]})
            if not isinstance(result, dict) or not isinstance(result.get("data"), list):
                raise PluginError("Codex returned an invalid skill catalog.")
            for group in result["data"]:
                if not isinstance(group, dict) or group.get("cwd") != str(root) or not isinstance(group.get("skills"), list):
                    continue
                if group.get("errors") and errors is not None:
                    errors.append({"kind": kind, "message": "Some skills could not be loaded. Check the Codex skill configuration."})
                for skill in group["skills"]:
                    if not isinstance(skill, dict) or skill.get("enabled") is not True:
                        continue
                    name, path = skill.get("name"), skill.get("path")
                    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{1,160}", name):
                        continue
                    if not isinstance(path, str) or not Path(path).is_absolute() or "\0" in path or len(path) > 4096:
                        continue
                    interface = skill.get("interface") if isinstance(skill.get("interface"), dict) else {}
                    owner = skill.get("pluginId")
                    token = name if ":" in name or not isinstance(owner, str) else owner.split("@", 1)[0] + ":" + name
                    if not re.fullmatch(r"[A-Za-z0-9._:-]{1,200}", token):
                        continue
                    entries.append({"id": "skill:" + hashlib.sha256(path.encode()).hexdigest(), "kind": kind,
                                    "name": token, "displayName": str(interface.get("displayName") or token)[:160],
                                    "description": str(interface.get("shortDescription") or skill.get("shortDescription") or skill.get("description") or "")[:500],
                                    "insertText": "$" + token, "native": {"type": "skill", "name": name, "path": path}})
        elif kind == "app":
            # Native app reads accept only loaded thread IDs. Discovery can use
            # the global snapshot for unopened history; sends load the thread
            # first and revalidate against its effective configuration.
            params = {}
            if thread_id:
                loaded = await self.codex.request("thread/loaded/list", {})
                if not isinstance(loaded, dict) or not isinstance(loaded.get("data"), list):
                    raise PluginError("Codex could not confirm the app configuration.")
                if thread_id in loaded["data"]:
                    params = {"threadId": thread_id}
            result = await self.codex.request("app/installed", params)
            if not isinstance(result, dict) or not isinstance(result.get("apps"), list):
                raise PluginError("Codex returned an invalid app catalog.")
            installed = [app for app in result["apps"] if isinstance(app, dict) and app.get("enabled") is True and app.get("callable") is True
                         and isinstance(app.get("id"), str) and re.fullmatch(r"[A-Za-z0-9_-]{1,160}", app["id"])][:100]
            if installed:
                metadata = await self.codex.request("app/read", {"appIds": [app["id"] for app in installed], **params})
                if not isinstance(metadata, dict) or not isinstance(metadata.get("apps"), list):
                    raise PluginError("Codex returned invalid app metadata.")
                names = {app["id"]: app for app in metadata["apps"] if isinstance(app, dict) and isinstance(app.get("id"), str)}
                for app in installed:
                    info = names.get(app["id"])
                    if not info:
                        continue
                    display = str(info.get("name") or app.get("runtimeName") or app["id"])
                    slug = re.sub(r"[^a-z0-9]+", "-", display.lower()).strip("-")
                    if not slug:
                        continue
                    entries.append({"id": "app:" + app["id"], "kind": kind, "name": slug, "displayName": display[:160],
                                    "description": str(info.get("description") or "")[:500], "insertText": "$" + slug,
                                    "native": {"type": "mention", "name": display, "path": "app://" + app["id"]}})
        return sorted({entry["id"]: entry for entry in entries}.values(), key=lambda entry: entry["displayName"].casefold())[:256]

    async def entries(self, cwd: str, thread_id: str | None = None) -> dict:
        self.root(cwd)
        kinds = ("skill", "plugin", "app")
        entries, errors = [], []
        results = await asyncio.gather(*(self.category(kind, cwd, thread_id, errors) for kind in kinds), return_exceptions=True)
        for kind, result in zip(kinds, results):
            if isinstance(result, BaseException):
                errors.append({"kind": kind, "message": f"{kind.title()}s could not be loaded. Retry after checking Codex."})
            else:
                entries.extend({key: value for key, value in entry.items() if key != "native"} for entry in result)
        return {"data": entries, "errors": errors}

    def file_entry(self, root: Path, path: Path) -> dict:
        if any(char in str(path) for char in ('\n', '\r', '"', '\\')):
            raise ValueError("Unsupported file reference")
        relative = str(path.relative_to(root))
        token = "@" + (f'"{relative}"' if any(char.isspace() for char in relative) else relative)
        return {"id": "file:" + quote(str(path.relative_to(self.workspace.root)), safe=""), "kind": "file", "name": relative,
                "displayName": path.name, "description": relative, "insertText": token}

    async def files(self, cwd: str, query: str) -> list[dict]:
        root = self.root(cwd)
        if not query:
            return []
        try:
            response = await self.codex.request("fuzzyFileSearch", {"query": query, "roots": [str(root)], "cancellationToken": None})
            if not isinstance(response, dict) or not isinstance(response.get("files"), list):
                raise PluginError("Codex returned an invalid file catalog.")
            entries = []
            for match in response["files"][:256]:
                if not isinstance(match, dict) or not isinstance(match.get("path"), str) or match.get("root") != str(root):
                    continue
                try:
                    path = self.workspace.resolve(str(root / match["path"]), must_exist=True)
                    path.relative_to(root)
                    if not path.is_file():
                        continue
                    entry = self.file_entry(root, path)
                    if len(entry["id"]) <= 256:
                        entries.append(entry)
                except (UnsafePath, OSError, ValueError, RuntimeError):
                    continue
            return list({entry["id"]: entry for entry in entries}.values())[:24]
        except CodexRPCError:
            raise PluginError("Workspace files could not be searched. Check the local Codex service.") from None

    async def resolve(self, identifiers: list[str], ask: str, cwd: str, thread_id: str) -> list[dict]:
        if not identifiers:
            return []
        root = self.root(cwd)
        catalogs = {}
        inputs = []
        for identifier in identifiers:
            kind, _, value = identifier.partition(":")
            if kind == "file":
                try:
                    path = self.workspace.resolve(unquote(value), must_exist=True)
                    path.relative_to(root)
                    if not path.is_file():
                        raise ValueError()
                    entry = self.file_entry(root, path)
                    if entry["id"] != identifier:
                        raise ValueError()
                except (UnsafePath, OSError, ValueError, RuntimeError):
                    raise PluginError("A selected file is unavailable. Review the message.") from None
            elif kind in ("skill", "plugin", "app"):
                if kind not in catalogs:
                    try:
                        catalogs[kind] = {entry["id"]: entry for entry in await self.category(kind, cwd, thread_id)}
                    except (CodexRPCError, CodexUnavailable):
                        raise PluginError("Selected mentions could not be verified. Check Codex before retrying.") from None
                entry = catalogs[kind].get(identifier)
            else:
                entry = None
            if entry is None or not literal_present(ask, entry["insertText"]):
                raise PluginError("A selected mention is unavailable or no longer present. Review the message.")
            if "native" in entry:
                inputs.append(entry["native"])
        return inputs
