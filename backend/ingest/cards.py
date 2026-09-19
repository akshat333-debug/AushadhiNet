"""One-tap confirmation cards (modular-plan.md §2.4): a low-confidence
field is never written silently -- it always produces a card naming that
field, sent back to the reporter for a one-tap confirm/correct.
"""
from __future__ import annotations

from dataclasses import dataclass

from backend.domain import ConfidenceSource, RecordStatus


@dataclass
class ConfirmationCard:
    text: str
    buttons: list[str]
    record_id: str
    low_fields: list[str]


def build(record, low_fields: list[str]) -> ConfirmationCard:
    field_list = ", ".join(low_fields)
    text = (
        f"Please confirm for {getattr(record, 'drug_id', 'this record')}: "
        f"we're not fully sure about {field_list}. Reply YES to confirm as read, "
        f"or send the correct value."
    )
    return ConfirmationCard(text=text, buttons=["Confirm", "Correct"], record_id=record.record_id, low_fields=low_fields)


def apply_reply(record, reply: dict):
    """One-tap confirm: patches the named field(s) and raises their
    confidence to 1.0 with source="manual" -- the officer's own confirming
    tap is now the source of truth for that field."""
    updated_fields = dict(record.confidence.field_confidence)
    for field_name, value in reply.items():
        if hasattr(record, field_name):
            setattr(record, field_name, value)
        updated_fields[field_name] = 1.0
    record.confidence.field_confidence = updated_fields
    record.confidence.source = ConfidenceSource.MANUAL
    record.status = RecordStatus.CONFIRMED  # a human just confirmed/corrected the flagged fields
    return record
