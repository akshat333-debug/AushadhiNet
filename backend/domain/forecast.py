"""Forecast (modular-plan.md §2.1). Grain distinguishes the real monthly
district benchmark from the synthetic weekly facility benchmark (modular-
plan.md §1's resolution of the two-grain / one-package gap)."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, model_validator

from backend.domain.enums import Grain


class Forecast(BaseModel):
    model_config = ConfigDict(extra="forbid")

    forecast_id: str
    grain: Grain
    entity_id: str  # facility_id (FACILITY_WEEK) or district_id (DISTRICT_MONTH)
    drug_id: str
    origin_date: date
    horizon: int  # weeks for FACILITY_WEEK, months for DISTRICT_MONTH
    p50: float
    p10: float
    p90: float
    stockout_prob: float
    model: str
    model_version: str
    features_hash: str

    @model_validator(mode="after")
    def _validate(self) -> "Forecast":
        if not (0.0 <= self.stockout_prob <= 1.0):
            raise ValueError("stockout_prob must be in [0, 1]")
        if not (self.p10 <= self.p50 <= self.p90):
            raise ValueError("quantiles must satisfy p10 <= p50 <= p90")
        if self.horizon <= 0:
            raise ValueError("horizon must be positive")
        return self
