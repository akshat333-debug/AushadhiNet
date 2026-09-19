"""BedCensus (modular-plan.md §2.1)."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, model_validator

from backend.domain.confidence import Confidence
from backend.domain.enums import RecordStatus


class BedCensus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    facility_id: str
    as_of_date: date
    beds_total: int
    beds_occupied: int
    admissions: int | None = None
    discharges: int | None = None
    status: RecordStatus = RecordStatus.PENDING
    confidence: Confidence
    raw_message_id: str

    @model_validator(mode="after")
    def _validate(self) -> "BedCensus":
        if self.beds_total < 0 or self.beds_occupied < 0:
            raise ValueError("bed counts must be >= 0")
        if self.beds_occupied > self.beds_total:
            raise ValueError("beds_occupied must be <= beds_total")
        return self
