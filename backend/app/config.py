from __future__ import annotations

import shlex
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


APPROVAL_POLICY_ALIASES = {
    "onRequest": "on-request",
    "unlessTrusted": "untrusted",
}
# The App Server represents granular policy as a structured object. The MVP's
# environment and REST controls intentionally expose only the three scalar modes.
VALID_APPROVAL_POLICIES = {"untrusted", "on-request", "never"}
SANDBOX_ALIASES = {
    "readOnly": "read-only",
    "workspaceWrite": "workspace-write",
    "dangerFullAccess": "danger-full-access",
}
VALID_SANDBOXES = {"read-only", "workspace-write", "danger-full-access"}


def normalize_approval_policy(value: str) -> str:
    normalized = APPROVAL_POLICY_ALIASES.get(value, value)
    if normalized not in VALID_APPROVAL_POLICIES:
        raise ValueError(f"unsupported approval policy: {value}")
    return normalized


def normalize_sandbox(value: str) -> str:
    normalized = SANDBOX_ALIASES.get(value, value)
    if normalized not in VALID_SANDBOXES:
        raise ValueError(f"unsupported sandbox mode: {value}")
    return normalized


def sandbox_policy(mode: str, writable_root: Path | None = None) -> dict[str, object]:
    normalized = normalize_sandbox(mode)
    if normalized == "read-only":
        return {"type": "readOnly", "networkAccess": False}
    if normalized == "danger-full-access":
        return {"type": "dangerFullAccess"}
    return {
        "type": "workspaceWrite",
        # Codex already treats the turn's cwd as writable. Additional roots are
        # capabilities, so do not implicitly grant the entire workspace mount.
        "writableRoots": [],
        "networkAccess": False,
        "excludeTmpdirEnvVar": False,
        "excludeSlashTmp": False,
    }


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CODEX_WEBUI_", env_file=".env", extra="ignore", populate_by_name=True
    )

    data_dir: Path = Field(
        default=Path("./data"),
        validation_alias=AliasChoices("CODEX_WEBUI_DATA_DIR", "DATA_DIR"),
    )
    database_file: Path | None = Field(
        default=None,
        validation_alias=AliasChoices("CODEX_WEBUI_DATABASE_PATH", "DATABASE_PATH"),
    )
    image_directory: Path | None = Field(
        default=None,
        validation_alias=AliasChoices("CODEX_WEBUI_IMAGE_LIBRARY_DIR", "IMAGE_LIBRARY_DIR"),
    )
    frontend_dist: Path | None = Field(
        default=None,
        validation_alias=AliasChoices("CODEX_WEBUI_FRONTEND_DIST", "FRONTEND_DIST"),
    )
    workspace_root: Path = Field(
        default_factory=Path.cwd,
        validation_alias=AliasChoices("CODEX_WEBUI_WORKSPACE_ROOT", "WORKSPACES_ROOT"),
    )
    codex_command: str = Field(
        default="codex app-server",
        validation_alias=AliasChoices("CODEX_WEBUI_CODEX_COMMAND", "CODEX_BIN"),
    )
    codex_enabled: bool = True
    approval_policy: str = Field(
        default="on-request",
        validation_alias=AliasChoices("CODEX_WEBUI_APPROVAL_POLICY", "DEFAULT_APPROVAL_POLICY"),
    )
    sandbox: str = Field(
        default="workspace-write",
        validation_alias=AliasChoices("CODEX_WEBUI_SANDBOX", "DEFAULT_SANDBOX"),
    )
    update_command: str | None = None
    max_file_bytes: int = 2 * 1024 * 1024
    max_image_bytes: int = 20 * 1024 * 1024
    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:8765",
            "http://localhost:8765",
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ]
    )
    # Starlette's TrustedHostMiddleware does not parse bracketed IPv6 hosts
    # correctly. Operators binding an IPv6/Tailscale name should explicitly set
    # the canonical DNS host through CODEX_WEBUI_ALLOWED_HOSTS.
    allowed_hosts: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["127.0.0.1", "localhost"]
    )
    max_protocol_line_bytes: int = 32 * 1024 * 1024
    experimental_api: bool = True
    realtime_feature_enabled: bool = False
    runtime: Literal["localhost-companion", "container"] = "localhost-companion"

    @field_validator(
        "data_dir", "database_file", "image_directory", "frontend_dist", "workspace_root",
        mode="before",
    )
    @classmethod
    def expand_path(cls, value: str | Path | None) -> Path | None:
        if value is None:
            return None
        return Path(value).expanduser().resolve()

    @field_validator("allowed_origins", "allowed_hosts", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value

    @field_validator("approval_policy")
    @classmethod
    def validate_approval_policy(cls, value: str) -> str:
        return normalize_approval_policy(value)

    @field_validator("sandbox")
    @classmethod
    def validate_sandbox(cls, value: str) -> str:
        return normalize_sandbox(value)

    @property
    def database_path(self) -> Path:
        return self.database_file or (self.data_dir / "codex-webui.sqlite3")

    @property
    def image_dir(self) -> Path:
        return self.image_directory or (self.data_dir / "images")

    @property
    def codex_argv(self) -> list[str]:
        argv = shlex.split(self.codex_command)
        # CODEX_BIN is commonly configured as the executable only.
        if len(argv) == 1:
            argv.append("app-server")
        has_realtime_override = any(
            index > 0
            and value == "realtime_conversation"
            and argv[index - 1] in {"--enable", "--disable"}
            for index, value in enumerate(argv)
        )
        if self.realtime_feature_enabled and not has_realtime_override and "app-server" in argv:
            argv_index = argv.index("app-server")
            argv[argv_index:argv_index] = ["--enable", "realtime_conversation"]
        return argv


def load_settings() -> Settings:
    return Settings()
