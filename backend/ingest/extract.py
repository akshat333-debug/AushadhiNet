"""Turns raw audio/image bytes into domain records with per-field
confidence (modular-plan.md §2.4, AC1/AC2).
"""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone

from backend.domain import Confidence, ConfidenceSource, RecordStatus, StockRecord
from backend.providers import factory
from backend.providers.base import Media

from backend.ingest.nlem import match as nlem_match
from backend.ingest.prompts import STOCK_REGISTER_PROMPT, STOCK_VOICE_PROMPT
from backend.ingest.schemas import StockExtraction


@dataclass
class ExtractionResult:
    records: list[StockRecord]
    confidence: Confidence
    transcript: str | None


def _to_stock_record(extraction: StockExtraction, facility_id: str, reporter_phone_hash: str, raw_message_id: str, source: ConfidenceSource) -> StockRecord:
    matches = nlem_match(extraction.drug_name, k=1)
    drug_id = matches[0].drug_id if matches else extraction.drug_name.strip().lower().replace(" ", "-")
    confidence = Confidence(field_confidence=extraction.confidence, overall=min(extraction.confidence.values(), default=0.0), source=source)
    return StockRecord(
        record_id=str(uuid.uuid4()), facility_id=facility_id, drug_id=drug_id,
        reported_at=datetime.now(timezone.utc), as_of_date=date.today(),
        on_hand=extraction.on_hand, received=extraction.received, dispensed=extraction.dispensed,
        batch_no=extraction.batch_no, expiry=extraction.expiry, status=RecordStatus.PENDING,
        confidence=confidence, reporter_phone_hash=reporter_phone_hash, raw_message_id=raw_message_id,
    )


def from_image(image: bytes, mime: str, facility_id: str, reporter_phone_hash: str) -> ExtractionResult:
    llm = factory.get("llm")
    raw_message_id = hashlib.sha256(image).hexdigest()[:16]
    extraction, field_confidence = llm.extract(
        STOCK_REGISTER_PROMPT, [Media(data=image, mime=mime)], StockExtraction,
    )
    extraction.confidence = {**extraction.confidence, **field_confidence} if field_confidence else extraction.confidence
    record = _to_stock_record(extraction, facility_id, reporter_phone_hash, raw_message_id, ConfidenceSource.GEMINI)
    overall = Confidence(field_confidence=extraction.confidence, overall=record.confidence.overall, source=ConfidenceSource.GEMINI)
    return ExtractionResult(records=[record], confidence=overall, transcript=None)


def from_audio(audio: bytes, mime: str, facility_id: str, reporter_phone_hash: str, lang_hint: str | None = None) -> ExtractionResult:
    speech = factory.get("speech")
    llm = factory.get("llm")
    raw_message_id = hashlib.sha256(audio).hexdigest()[:16]

    transcript = speech.transcribe(audio, mime, lang_hint)
    extraction, field_confidence = llm.extract(
        f"{STOCK_VOICE_PROMPT}\n\nTranscript: {transcript.text}", [], StockExtraction,
    )
    if field_confidence:
        extraction.confidence = {**extraction.confidence, **field_confidence}
    record = _to_stock_record(extraction, facility_id, reporter_phone_hash, raw_message_id, ConfidenceSource.CHIRP)
    overall = Confidence(field_confidence=extraction.confidence, overall=record.confidence.overall, source=ConfidenceSource.CHIRP)
    return ExtractionResult(records=[record], confidence=overall, transcript=transcript.text)
