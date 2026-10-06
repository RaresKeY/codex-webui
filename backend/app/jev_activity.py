"""Bounded decision metadata, never prompts, provider bodies or error messages."""
from __future__ import annotations

import json
import sqlite3
import time
from typing import Any

from .database import Database
from .models import utc_now
from .task_router import MODELS, EFFORTS, DIAGNOSTICS, DIAGNOSTIC_CHOICES, probability


def safe_decision(decision: dict[str, Any]) -> dict[str, Any]:
    result = {key: decision[key] for key, allowed in (("model", MODELS), ("effort", EFFORTS)) if isinstance(decision.get(key), str) and decision[key] in allowed}
    policy = decision.get("policy")
    if isinstance(policy, str) and len(policy) <= 100:
        result["policy"] = policy
    for key in ("modelConfidence", "effortConfidence"):
        if probability(decision.get(key)):
            result[key] = decision[key]
    for key, allowed in (("modelProbabilities", MODELS), ("effortProbabilities", EFFORTS)):
        values = decision.get(key)
        if isinstance(values, dict) and set(values) == allowed and all(probability(value) for value in values.values()):
            result[key] = values
    usage = decision.get("usage")
    if isinstance(usage, dict) and all(type(usage.get(key)) is int and usage[key] >= 0 for key in ("input_tokens", "output_tokens")):
        result["usage"] = {key: usage[key] for key in ("input_tokens", "output_tokens")}
    preparation = decision.get("preparation")
    if isinstance(preparation, dict):
        result["preparation"] = {}
        for field in DIAGNOSTICS:
            answer = preparation.get(field)
            if not isinstance(answer, dict):
                continue
            values = answer.get("probabilities")
            if isinstance(answer.get("choice"), str) and answer["choice"] in DIAGNOSTIC_CHOICES and probability(answer.get("confidence")) and isinstance(values, dict) and set(values) == DIAGNOSTIC_CHOICES and all(probability(value) for value in values.values()):
                result["preparation"][field] = {"choice": answer["choice"], "confidence": answer["confidence"], "probabilities": values}
    return result


class JevActivity:
    def __init__(self, db: Database, publish=None):
        self.db = db
        self.publish = publish
        self.id: int | None = None
        self.started = time.monotonic()

    async def begin(self, thread_id: str, source: str) -> None:
        self.started = time.monotonic()
        now = utc_now()
        try:
            self.id = await self.db.execute(
                "INSERT INTO jev_activity(thread_id,source,status,stage,started_at,updated_at) VALUES(?,?,'pending','routing',?,?)",
                (thread_id, source, now, now),
            )
            await self.emit()
        except sqlite3.Error:
            pass  # Observability cannot turn a successful send into a retry.

    async def update(self, status: str, stage: str, decision: dict[str, Any] | None = None, turn_id: str | None = None) -> None:
        if self.id is None:
            return
        try:
            await self.db.execute(
                "UPDATE jev_activity SET status=?,stage=?,updated_at=?,duration_ms=?,"
                "decision_json=COALESCE(?,decision_json),turn_id=COALESCE(?,turn_id) WHERE id=?",
                (status, stage, utc_now(), round((time.monotonic() - self.started) * 1000),
                 json.dumps(safe_decision(decision)) if decision is not None else None, turn_id, self.id),
            )
            await self.emit()
        except sqlite3.Error:
            pass


    async def emit(self) -> None:
        if self.publish is None or self.id is None:
            return
        row = await self.db.fetchone("SELECT * FROM jev_activity WHERE id=?", (self.id,))
        if row:
            raw = row.pop("decision_json")
            row["decision"] = json.loads(raw) if raw else None
            try:
                await self.publish({"method": "webui/jevActivity", "params": {"threadId": row["thread_id"], "activity": row}})
            except Exception:
                pass  # Optional telemetry must never fail an acknowledged submission.


async def activity_page(db: Database, before: int | None, limit: int, thread_id: str | None = None) -> dict[str, Any]:
    rows = await db.fetchall(
        "SELECT * FROM jev_activity WHERE (? IS NULL OR id < ?) AND (? IS NULL OR (thread_id=? AND source!='preview')) ORDER BY id DESC LIMIT ?",
        (before, before, thread_id, thread_id, limit + 1),
    )
    items = rows[:limit]
    for row in items:
        raw = row.pop("decision_json")
        row["decision"] = json.loads(raw) if raw else None
    return {"data": items, "nextCursor": items[-1]["id"] if len(rows) > limit else None}
