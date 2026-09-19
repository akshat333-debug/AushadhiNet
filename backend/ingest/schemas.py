"""Gemini structured-output schemas (modular-plan.md §2.4): thin wrappers
over the domain models with a sibling `_confidence` dict, since Gemini's
`response_schema` needs a flat, JSON-schema-friendly shape rather than the
full domain model (which carries IDs and status the model shouldn't set).
"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class StockExtraction(BaseModel):
    """What Gemini/Chirp extraction returns for a stock report -- one
    entry per drug line on the register or in the voice note."""
    drug_name: str = Field(description="the drug name as written or spoken, not yet normalised against NLEM")
    on_hand: int = Field(description="current stock on hand, in the drug's dispensing unit")
    received: int | None = Field(default=None, description="units received since the last report, if mentioned")
    dispensed: int | None = Field(default=None, description="units dispensed since the last report, if mentioned")
    batch_no: str | None = Field(default=None)
    expiry: date | None = Field(default=None)
    confidence: dict[str, float] = Field(
        description="per-field confidence in [0,1] for on_hand, received, dispensed, batch_no, expiry"
    )


class BedCensusExtraction(BaseModel):
    beds_total: int
    beds_occupied: int
    admissions: int | None = None
    discharges: int | None = None
    confidence: dict[str, float]


class CheckInExtraction(BaseModel):
    staff_name_or_id: str
    role: str = Field(description="ANM, MO, pharmacist, lab or other")
    confidence: dict[str, float]
