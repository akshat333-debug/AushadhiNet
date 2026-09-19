"""Plain-text WhatsApp updates (modular-plan.md §2.4): a deterministic
rule-based parser, not an LLM call -- much cheaper, and text is the path a
tech-savvy officer uses precisely because it is unambiguous ("ORS 50" is
not a judgement call the way a blurry photo is). Falls back to leaving
the line unparsed (not guessed) if it doesn't match the simple pattern.
"""
from __future__ import annotations

import hashlib
import re
import uuid
from datetime import date, datetime, timezone

from backend.domain import Confidence, ConfidenceSource, RecordStatus, StockRecord

from backend.ingest.extract import ExtractionResult
from backend.ingest.nlem import match as nlem_match

_LINE_RE = re.compile(r"^\s*(?P<drug>[A-Za-z][A-Za-z0-9 .()%\-]*?)\s*[:\-]?\s*(?P<qty>\d+)\s*$")


def from_text(body: str, facility_id: str, reporter_phone_hash: str) -> ExtractionResult:
    raw_message_id = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
    records: list[StockRecord] = []

    for line in body.splitlines():
        m = _LINE_RE.match(line)
        if not m:
            continue
        drug_name, qty = m.group("drug").strip(), int(m.group("qty"))
        if not drug_name:
            continue
        matches = nlem_match(drug_name, k=1)
        drug_id = matches[0].drug_id if matches else drug_name.lower().replace(" ", "-")
        confidence = Confidence(field_confidence={"on_hand": 1.0}, overall=1.0, source=ConfidenceSource.MANUAL)
        records.append(StockRecord(
            record_id=str(uuid.uuid4()), facility_id=facility_id, drug_id=drug_id,
            reported_at=datetime.now(timezone.utc), as_of_date=date.today(),
            on_hand=qty, status=RecordStatus.PENDING, confidence=confidence,
            reporter_phone_hash=reporter_phone_hash, raw_message_id=raw_message_id,
        ))

    if not records:
        overall = Confidence(field_confidence={}, overall=0.0, source=ConfidenceSource.MANUAL)
        return ExtractionResult(records=[], confidence=overall, transcript=body)

    weakest = min(records, key=lambda r: r.confidence.overall)
    return ExtractionResult(records=records, confidence=weakest.confidence, transcript=body)
