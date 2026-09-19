"""CheckIn (modular-plan.md §2.1). geofence_ok is computed by ingest and
stored here, not recomputed downstream."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.domain.enums import RecordStatus, StaffRole


class CheckIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    facility_id: str
    staff_id_hash: str
    role: StaffRole
    at: datetime
    lat: float
    lon: float
    distance_m: float
    geofence_ok: bool
    status: RecordStatus = RecordStatus.PENDING
    raw_message_id: str
