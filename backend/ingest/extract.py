"""Turns raw audio/image bytes into domain records with per-field
confidence (modular-plan.md §2.4, AC1/AC2).
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from backend.domain import Confidence, ConfidenceSource, RecordStatus, StockRecord
from backend.providers import factory
from backend.providers.base import Media, ProviderError

from backend.ingest.nlem import match as nlem_match
from backend.ingest.prompts import STOCK_REGISTER_PROMPT, STOCK_VOICE_PROMPT
from backend.ingest.schemas import StockExtraction, StockPage

log = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    records: list[StockRecord]
    confidence: Confidence
    transcript: str | None
    rejected: list[str] = field(default_factory=list)  # lines with a quantity we will not guess at (negative, decimal)


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


def _too_small_to_read(image: bytes, min_side: int = 64) -> bool:
    """Gemini invents rows for a near-blank image (seen live: a 1x1 PNG came back as three
    medicines), so an image too small to hold a legible line never reaches it."""
    import io

    from PIL import Image, UnidentifiedImageError
    try:
        width, height = Image.open(io.BytesIO(image)).size
    except (UnidentifiedImageError, OSError):
        return False  # not decodable here; the model call decides
    return min(width, height) < min_side


def from_image(image: bytes, mime: str, facility_id: str, reporter_phone_hash: str) -> ExtractionResult:
    """Every drug line on a register photo. A photo the model cannot read gives no
    records (the reporter is asked to type it) rather than an error."""
    raw_message_id = hashlib.sha256(image).hexdigest()[:16]
    if _too_small_to_read(image):
        return ExtractionResult(records=[], confidence=Confidence(overall=0.0, source=ConfidenceSource.GEMINI), transcript=None)
    llm = factory.get("llm")
    try:
        page, _ = llm.extract(STOCK_REGISTER_PROMPT, [Media(data=image, mime=mime)], StockPage)
    except ProviderError as e:
        log.warning("photo read failed, nurse asked to type it: %s", str(e)[:300])
        return ExtractionResult(records=[], confidence=Confidence(overall=0.0, source=ConfidenceSource.GEMINI), transcript=None)
    records = [
        _to_stock_record(row, facility_id, reporter_phone_hash, raw_message_id, ConfidenceSource.GEMINI)
        for row in page.rows
    ]
    overall = min((r.confidence.overall for r in records), default=0.0)
    return ExtractionResult(records=records, confidence=Confidence(overall=overall, source=ConfidenceSource.GEMINI), transcript=None)


def from_audio(audio: bytes, mime: str, facility_id: str, reporter_phone_hash: str, lang_hint: str | None = None) -> ExtractionResult:
    speech = factory.get("speech")
    llm = factory.get("llm")
    raw_message_id = hashlib.sha256(audio).hexdigest()[:16]

    transcript = speech.transcribe(audio, mime, lang_hint)
    # Chirp writes spoken numbers as digits ("ORS 50 Zinc 120"), which the text parser reads
    # exactly, several items at once; Gemini is the fallback for numbers said as words.
    from backend.ingest.parse_text import from_text
    parsed = from_text(transcript.text, facility_id, reporter_phone_hash)
    if parsed.records:
        records = [r.model_copy(update={"raw_message_id": raw_message_id, "confidence": r.confidence.model_copy(update={"source": ConfidenceSource.CHIRP})})
                   for r in parsed.records]
        return ExtractionResult(records=records, confidence=parsed.confidence.model_copy(update={"source": ConfidenceSource.CHIRP}), transcript=transcript.text)
    extraction, field_confidence = llm.extract(
        f"{STOCK_VOICE_PROMPT}\n\nTranscript: {transcript.text}", [], StockExtraction,
    )
    if field_confidence:
        extraction.confidence = {**field_confidence, **extraction.confidence}  # what the model reported wins; unreported fields stay at the provider floor
    record = _to_stock_record(extraction, facility_id, reporter_phone_hash, raw_message_id, ConfidenceSource.CHIRP)
    overall = Confidence(field_confidence=extraction.confidence, overall=record.confidence.overall, source=ConfidenceSource.CHIRP)
    return ExtractionResult(records=[record], confidence=overall, transcript=transcript.text)
