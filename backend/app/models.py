from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .config import normalize_approval_policy, normalize_sandbox


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ThreadStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cwd: str | None = None
    model: str | None = None
    approval_policy: str | None = None
    sandbox: str | None = None
    ephemeral: bool = False

    @field_validator("approval_policy")
    @classmethod
    def validate_approval_policy(cls, value: str | None) -> str | None:
        return normalize_approval_policy(value) if value is not None else None

    @field_validator("sandbox")
    @classmethod
    def validate_sandbox(cls, value: str | None) -> str | None:
        return normalize_sandbox(value) if value is not None else None


class ThreadResume(BaseModel):
    cwd: str | None = None
    model: str | None = None


class RouteRequest(BaseModel):
    input: str = Field(min_length=1, max_length=24_000)


class ThreadName(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class TurnStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input: str = Field(min_length=1, max_length=24_000)
    approval_policy: str | None = None
    sandbox: str | None = None
    plugins: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("plugins")
    @classmethod
    def validate_plugins(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value) or any(not item or len(item) > 256 for item in value):
            raise ValueError("plugins must contain unique bounded identifiers")
        return value

    @field_validator("input")
    @classmethod
    def preserve_nonblank_input(cls, value: str) -> str:
        if not value.strip() or len(value.encode("utf-8")) > 24_000:
            raise ValueError("input must be nonblank text under 24 KB")
        return value

    @field_validator("approval_policy")
    @classmethod
    def validate_approval_policy(cls, value: str | None) -> str | None:
        return normalize_approval_policy(value) if value is not None else None

    @field_validator("sandbox")
    @classmethod
    def validate_sandbox(cls, value: str | None) -> str | None:
        return normalize_sandbox(value) if value is not None else None


class TurnSteer(BaseModel):
    input: str = Field(min_length=1)
    expected_turn_id: str | None = None


class ApprovalResponse(BaseModel):
    response: dict[str, Any]


class RealtimeStart(BaseModel):
    sdp: str = Field(min_length=1, max_length=1_000_000)
    voice: Literal[
        "alloy", "arbor", "ash", "ballad", "breeze", "cedar", "coral", "cove",
        "echo", "ember", "juniper", "maple", "marin", "sage", "shimmer", "sol",
        "spruce", "vale", "verse",
    ] | None = None
    # The public App Server docs explicitly reject realtime v2 over WebRTC.
    version: Literal["v1", "v3"] | None = None
    model: str | None = None
    include_startup_context: bool | None = None


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    color: str | None = Field(default=None, max_length=32)
    workspace: str = "."


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    color: str | None = Field(default=None, max_length=32)
    workspace: str | None = None


class ChatMetadataUpdate(BaseModel):
    project_id: int | None = None
    pinned: bool | None = None


class SettingValue(BaseModel):
    value: Any


class ScheduledTaskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    prompt: str = Field(min_length=1)
    schedule_type: Literal["interval", "cron"]
    schedule: str
    workspace: str = "."
    thread_id: str | None = None
    enabled: bool = True

    @field_validator("schedule")
    @classmethod
    def validate_schedule(cls, value: str, info: Any) -> str:
        if not value.strip():
            raise ValueError("schedule must not be blank")
        return value.strip()


class ScheduledTaskUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    prompt: str | None = Field(default=None, min_length=1)
    schedule_type: Literal["interval", "cron"] | None = None
    schedule: str | None = None
    workspace: str | None = None
    thread_id: str | None = None
    enabled: bool | None = None


class FileWrite(BaseModel):
    content: str
