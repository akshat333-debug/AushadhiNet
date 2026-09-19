"""Append-only audit log for every agent tool call (modular-plan.md §2.6):
`log()` is called on every tool entry and exit, so a full record exists of
what the agent read and what it (attempted to) do.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from backend.domain import AuditEvent
from backend.providers import factory


def log(actor: str, action: str, target_id: str, payload: dict, jurisdiction: str) -> AuditEvent:
    event = AuditEvent(
        event_id=str(uuid.uuid4()), at=datetime.now(timezone.utc), actor=actor,
        action=action, target_id=target_id, payload_json=json.dumps(payload, default=str),
        jurisdiction=jurisdiction,
    )
    factory.get("store_live").put("audit_events", event.event_id, event)
    return event


def log_tool_call(tool_name: str, officer_uid: str, jurisdiction: str, args: dict, result_summary: str) -> None:
    log(actor=f"agent:{officer_uid}", action=f"tool_call:{tool_name}:entry", target_id=tool_name, payload=args, jurisdiction=jurisdiction)
    log(actor=f"agent:{officer_uid}", action=f"tool_call:{tool_name}:exit", target_id=tool_name, payload={"result": result_summary}, jurisdiction=jurisdiction)
