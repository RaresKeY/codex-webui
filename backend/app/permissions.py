"""Explicit chat permission presets; native managed restrictions remain authoritative."""
from typing import Literal

from .config import Settings, sandbox_policy

PermissionMode = Literal["default", "full-auto", "yolo"]


def permission_overrides(mode: PermissionMode, settings: Settings) -> dict:
    return {
        "approvalPolicy": "never" if mode == "yolo" else settings.approval_policy if mode == "default" else "on-request",
        "approvalsReviewer": "auto_review" if mode == "full-auto" else "user",
        "sandboxPolicy": sandbox_policy(settings.sandbox if mode == "default" else "danger-full-access"),
    }
