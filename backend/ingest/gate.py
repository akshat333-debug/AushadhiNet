"""The confidence gate (modular-plan.md §2.4): the "never silent write"
rule from project.md FR2. Any field below threshold means the record
stays pending and a confirmation card is generated -- it is never written
as confirmed based on a guess.
"""
from __future__ import annotations

from dataclasses import dataclass

from backend.domain import RecordStatus

from backend.ingest.cards import ConfirmationCard, build as build_card


@dataclass
class GateDecision:
    confirmed: list
    pending: list
    card: ConfirmationCard | None


def apply(records: list, threshold: float, lang: str = "en") -> GateDecision:
    confirmed, pending = [], []
    card: ConfirmationCard | None = None

    for record in records:
        low_fields = record.confidence.low_fields(threshold)
        if low_fields:
            record.status = RecordStatus.PENDING
            pending.append(record)
            if card is None:  # one card per gate call; the caller sends it once, covering all pending records
                card = build_card(record, low_fields, lang)
        else:
            record.status = RecordStatus.CONFIRMED
            confirmed.append(record)

    return GateDecision(confirmed=confirmed, pending=pending, card=card)
