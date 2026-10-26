"""The confidence gate (modular-plan.md §2.4): the "never silent write"
rule from project.md FR2. Any field below threshold means the record
stays pending and a confirmation card is generated -- it is never written
as confirmed based on a guess.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from backend.domain import RecordStatus

from backend.ingest.cards import ConfirmationCard, build as build_card


@dataclass
class GateDecision:
    confirmed: list
    pending: list
    card: ConfirmationCard | None
    rejected: list = field(default_factory=list)  # lines with an unusable quantity, named back to the reporter


def apply(records: list, threshold: float, lang: str = "en") -> GateDecision:
    confirmed, pending, low = [], [], []
    for record in records:
        low_fields = record.confidence.low_fields(threshold)
        if low_fields:
            record.status = RecordStatus.PENDING
            pending.append(record)
            low += [f for f in low_fields if f not in low]
        else:
            record.status = RecordStatus.CONFIRMED
            confirmed.append(record)

    # One card covering every pending record, each with the quantity read: YES confirms exactly what it shows.
    card: ConfirmationCard | None = build_card(pending, low, lang) if pending else None
    return GateDecision(confirmed=confirmed, pending=pending, card=card)
