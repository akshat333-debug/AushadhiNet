"""AuditEvent — append-only (modular-plan.md §2.1)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    at: datetime
    actor: str  # "agent" | "officer:{uid}" | "system"
    action: str
    target_id: str
    payload_json: str
    jurisdiction: str
