"""DoD test for backend/ingest/gate.py + cards.py (step 28): the
'never silent write' rule."""
from __future__ import annotations

from datetime import date, datetime, timezone

from backend.domain import Confidence, ConfidenceSource, RecordStatus, StockRecord
from backend.ingest.cards import apply_reply, build
from backend.ingest.gate import apply


def _record(**confidence_fields) -> StockRecord:
    return StockRecord(
        record_id="r1", facility_id="F1", drug_id="ors",
        reported_at=datetime.now(timezone.utc), as_of_date=date.today(), on_hand=10,
        confidence=Confidence(field_confidence=confidence_fields, overall=min(confidence_fields.values()), source=ConfidenceSource.GEMINI),
        reporter_phone_hash="h1", raw_message_id="m1",
    )


def test_low_confidence_field_always_lands_in_pending_with_card_naming_it():
    record = _record(on_hand=0.6, drug_id=0.95)
    decision = apply([record], threshold=0.85)
    assert decision.confirmed == []
    assert decision.pending == [record]
    assert record.status == RecordStatus.PENDING
    assert decision.card is not None
    assert "on_hand" in decision.card.low_fields
    assert "the quantity" in decision.card.text


def test_high_confidence_record_is_confirmed_without_a_card():
    record = _record(on_hand=0.95, drug_id=0.99)
    decision = apply([record], threshold=0.85)
    assert decision.confirmed == [record]
    assert decision.pending == []
    assert record.status == RecordStatus.CONFIRMED


def test_never_writes_confirmed_for_a_low_confidence_field():
    """The core rule: no matter how many other fields are high-confidence,
    one low field keeps the whole record pending."""
    record = _record(on_hand=0.99, drug_id=0.99, expiry=0.5)
    decision = apply([record], threshold=0.85)
    assert record.status == RecordStatus.PENDING
    assert "expiry" in decision.card.low_fields


def test_mixed_batch_splits_confirmed_and_pending():
    good = _record(on_hand=0.95)
    bad = _record(on_hand=0.5)
    decision = apply([good, bad], threshold=0.85)
    assert decision.confirmed == [good]
    assert decision.pending == [bad]


def test_apply_reply_confirms_and_raises_confidence_to_1():
    record = _record(on_hand=0.6)
    apply_reply(record, {"on_hand": 25})
    assert record.on_hand == 25
    assert record.confidence.field_confidence["on_hand"] == 1.0
    assert record.confidence.source == ConfidenceSource.MANUAL
    assert record.status == RecordStatus.CONFIRMED


def test_card_text_names_the_specific_low_field():
    record = _record(on_hand=0.99, expiry=0.4)
    card = build(record, ["expiry"])
    assert "expiry" in card.text
    assert card.record_id == record.record_id
