"""StockRecord (modular-plan.md §2.1)."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, model_validator

from backend.domain.confidence import Confidence
from backend.domain.enums import RecordStatus


class StockRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    facility_id: str
    drug_id: str
    reported_at: datetime
    as_of_date: date
    on_hand: int
    received: int | None = None
    dispensed: int | None = None
    unusable: int | None = None
    batch_no: str | None = None
    expiry: date | None = None
    status: RecordStatus = RecordStatus.PENDING
    confidence: Confidence
    reporter_phone_hash: str
    raw_message_id: str

    @model_validator(mode="after")
    def _validate(self) -> "StockRecord":
        if self.on_hand < 0:
            raise ValueError("on_hand must be >= 0")
        if self.expiry is not None and self.expiry < self.as_of_date:
            # Expired-before-reported is almost always a misread date, not a
            # real fact: force it low-confidence rather than accept silently.
            fc = dict(self.confidence.field_confidence)
            fc["expiry"] = min(fc.get("expiry", 0.0), 0.0)
            object.__setattr__(self.confidence, "field_confidence", fc)
        return self
