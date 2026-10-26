"""Consumes queued raw messages, runs extraction, applies the confidence
gate, and writes confirmed records to both stores (modular-plan.md §2.3,
architecture.md §4 steps 2-4; AC3 covers the bed-census and check-in
variants here too).
"""
from __future__ import annotations

import base64
import logging

from backend.config import get_settings
from backend.domain import BedCensus, CheckIn, ConfidenceSource, RecordStatus, StaffRole
from backend.providers import factory
from backend.providers.base import ProviderError
from backend.runtime import note_confirmed

from backend.ingest.cards import build_photo_card
from backend.ingest.extract import from_audio, from_image
from backend.ingest.gate import apply as gate_apply
from backend.ingest.media import validate as validate_media
from backend.ingest.parse_text import from_text

log = logging.getLogger(__name__)


def _haversine_m(lat1, lon1, lat2, lon2) -> float:
    import math
    r_m = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r_m * math.asin(math.sqrt(a))


def handle_stock_message(payload: dict, facility_id: str):
    """payload: {body, num_media, media_url, media_content_type,
    reporter_phone_hash}. Downloads media if present, extracts, gates,
    and writes confirmed records; pending records get a confirmation card
    sent back instead."""
    settings = get_settings()
    messaging = factory.get("messaging")
    live_store = factory.get("store_live")
    history_store = factory.get("store_history")

    if payload.get("num_media", 0) > 0 and payload.get("media_url"):
        media_bytes = _download_media(payload["media_url"], settings)
        content_type = payload.get("media_content_type", "")
        try:
            validate_media(content_type, len(media_bytes), media_bytes)
        except ProviderError as e:
            log.warning("media rejected, nurse asked to type it: %s", e)
            content_type, media_bytes = "", None
        if media_bytes is None:
            result = from_text("", facility_id, payload["reporter_phone_hash"])  # nothing usable: the reply asks to type it
        elif content_type.startswith("audio/"):
            try:
                result = from_audio(media_bytes, content_type, facility_id, payload["reporter_phone_hash"], payload.get("lang"))
            except ProviderError as e:
                log.warning("voice note not transcribed, nurse asked to type it: %s", str(e)[:300])
                result = from_text("", facility_id, payload["reporter_phone_hash"])  # nothing heard: the reply asks to type it
        else:
            result = from_image(media_bytes, content_type, facility_id, payload["reporter_phone_hash"])
    else:
        result = from_text(payload.get("body") or "", facility_id, payload["reporter_phone_hash"])

    lang = payload.get("lang", "en")
    media = payload.get("num_media", 0) > 0
    voice = media and payload.get("media_content_type", "").startswith("audio/")
    # A model reading a photo or hearing a voice note can be confidently wrong, so every such
    # read waits for the reporter's YES, shown with the values as read (and what was heard).
    decision = gate_apply(result.records, float("inf") if media else settings.confidence_threshold, lang)
    if media and decision.pending:
        decision.card = build_photo_card(decision.pending, lang, heard=result.transcript if voice else None)

    for record in decision.confirmed:
        live_store.put("stock_records", record.record_id, record)
        note_confirmed(record)
        history_store.insert("stock_records", [record.model_dump(mode="json")])

    for record in decision.pending:
        live_store.put("stock_records", record.record_id, record)  # visible as pending, not silently dropped

    if decision.card is not None:
        messaging.send_buttons(payload["from"], decision.card.text, decision.card.buttons)
    decision.rejected = result.rejected
    if result.rejected:
        from backend.i18n import msg
        messaging.send_text(payload["from"], msg(lang, "bad_quantity", lines="; ".join(result.rejected)))
    return decision


def _download_media(media_url: str, settings) -> bytes:
    """In local/demo mode, `media_url` is a data: URI carrying the fixture
    bytes directly (no real network fetch needed); in cloud mode, this
    would authenticate to Twilio's media endpoint."""
    if media_url.startswith("data:"):
        _, encoded = media_url.split(",", 1)
        return base64.b64decode(encoded)
    if settings.mode == "cloud":
        import requests
        from requests.auth import HTTPBasicAuth
        response = requests.get(media_url, auth=HTTPBasicAuth(settings.twilio_account_sid, settings.twilio_auth_token), timeout=10)
        response.raise_for_status()
        return response.content
    raise ValueError(f"cannot resolve media_url in local mode: {media_url}")


def handle_bed_census(payload: dict, facility_id: str, beds_total: int, beds_occupied: int) -> BedCensus:
    """AC3: bed census variant. A simple structured message, not free text
    -- the officer sends fixed fields, so no LLM extraction is needed."""
    from backend.domain import Confidence
    import hashlib
    import uuid
    from datetime import date

    record = BedCensus(
        record_id=str(uuid.uuid4()), facility_id=facility_id, as_of_date=date.today(),
        beds_total=beds_total, beds_occupied=beds_occupied, status=RecordStatus.CONFIRMED,
        confidence=Confidence(field_confidence={"beds_total": 1.0, "beds_occupied": 1.0}, overall=1.0, source=ConfidenceSource.MANUAL),
        raw_message_id=hashlib.sha256(payload.get("message_sid", "").encode()).hexdigest()[:16],
    )
    factory.get("store_live").put("bed_census", record.record_id, record)
    factory.get("store_history").insert("bed_census", [record.model_dump(mode="json")])
    return record


def handle_checkin(payload: dict, facility_id: str, staff_id_hash: str, role: StaffRole, lat: float, lon: float, facility_lat: float, facility_lon: float) -> CheckIn:
    """AC3: a check-in outside the facility geofence is flagged, not
    rejected -- it still gets recorded, with geofence_ok=False for the
    dashboard/officer to see."""
    import hashlib
    import uuid
    from datetime import datetime, timezone

    settings = get_settings()
    distance = _haversine_m(lat, lon, facility_lat, facility_lon)
    record = CheckIn(
        record_id=str(uuid.uuid4()), facility_id=facility_id, staff_id_hash=staff_id_hash, role=role,
        at=datetime.now(timezone.utc), lat=lat, lon=lon, distance_m=distance,
        geofence_ok=distance <= settings.geofence_radius_m, status=RecordStatus.CONFIRMED,
        raw_message_id=hashlib.sha256(payload.get("message_sid", "").encode()).hexdigest()[:16],
    )
    factory.get("store_live").put("checkins", record.record_id, record)
    factory.get("store_history").insert("checkins", [record.model_dump(mode="json")])
    return record
