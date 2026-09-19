"""Shared enums for domain models (modular-plan.md §2.1)."""
from __future__ import annotations

from enum import Enum


class FacilityType(str, Enum):
    SC = "SC"
    PHC = "PHC"
    CHC = "CHC"
    SDH = "SDH"
    DH = "DH"


class RecordStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class StaffRole(str, Enum):
    ANM = "ANM"
    MO = "MO"
    PHARMACIST = "pharmacist"
    LAB = "lab"
    OTHER = "other"


class Grain(str, Enum):
    DISTRICT_MONTH = "DISTRICT_MONTH"
    FACILITY_WEEK = "FACILITY_WEEK"


class OrderKind(str, Enum):
    DRUG_TRANSFER = "drug_transfer"
    DEPUTATION = "deputation"
    REFERRAL = "referral"


class OrderStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISPATCHED = "dispatched"
    RECEIVED = "received"
    EXPIRED = "expired"


class ConfidenceSource(str, Enum):
    GEMINI = "gemini"
    CHIRP = "chirp"
    MANUAL = "manual"
    IMPORT = "import"
