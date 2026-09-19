"""Facility and drug master models (modular-plan.md §2.1)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from backend.domain.enums import FacilityType


class Facility(BaseModel):
    model_config = ConfigDict(extra="forbid")

    facility_id: str
    name: str
    state_code: str
    district_id: str
    block: str | None = None
    facility_type: FacilityType
    lat: float
    lon: float
    beds_sanctioned: int = 0
    has_cold_chain: bool = False
    parent_facility_id: str | None = None

    @field_validator("lat")
    @classmethod
    def _lat_range(cls, v: float) -> float:
        if not (-90.0 <= v <= 90.0):
            raise ValueError("lat out of range")
        return v

    @field_validator("lon")
    @classmethod
    def _lon_range(cls, v: float) -> float:
        if not (-180.0 <= v <= 180.0):
            raise ValueError("lon out of range")
        return v

    @field_validator("beds_sanctioned")
    @classmethod
    def _beds_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("beds_sanctioned must be >= 0")
        return v


class Drug(BaseModel):
    model_config = ConfigDict(extra="forbid")

    drug_id: str
    name: str
    strength: str | None = None
    form: str | None = None
    unit: str
    nlem_level: str  # "P" | "S" | "T"
    cold_chain: bool = False
    aliases: list[str] = []

    @field_validator("nlem_level")
    @classmethod
    def _level_valid(cls, v: str) -> str:
        if v not in ("P", "S", "T"):
            raise ValueError("nlem_level must be P, S or T")
        return v


class Contact(BaseModel):
    """A registered WhatsApp number and the facility it reports for (doc id = phone)."""
    model_config = ConfigDict(extra="forbid")

    phone: str
    facility_id: str
