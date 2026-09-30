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


def build(record, low_fields: list[str], lang: str = "en") -> ConfirmationCard:
    from backend.i18n import MESSAGES, drug_name, msg
    field_list = ", ".join(msg(lang, f"field_{f}") if f"field_{f}" in MESSAGES["en"] else f for f in low_fields)
    drug = drug_name(getattr(record, "drug_id", ""), lang) or "this record"
    return ConfirmationCard(
        text=msg(lang, "card", drug=drug, fields=field_list),
        buttons=[msg(lang, "btn_confirm"), msg(lang, "btn_correct")],
        record_id=record.record_id, low_fields=low_fields,
    )


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
