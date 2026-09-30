"""Consumes queued raw messages, runs extraction, applies the confidence
gate, and writes confirmed records to both stores (modular-plan.md §2.3,
architecture.md §4 steps 2-4; AC3 covers the bed-census and check-in
variants here too).
"""
from __future__ import annotations

import base64

from backend.config import get_settings
from backend.domain import BedCensus, CheckIn, ConfidenceSource, RecordStatus, StaffRole
from backend.providers import factory

from backend.ingest.extract import from_audio, from_image
from backend.ingest.gate import apply as gate_apply
from backend.ingest.parse_text import from_text


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
        if content_type.startswith("audio/"):
            result = from_audio(media_bytes, content_type, facility_id, payload["reporter_phone_hash"])
        else:
            result = from_image(media_bytes, content_type, facility_id, payload["reporter_phone_hash"])
    else:
        result = from_text(payload.get("body") or "", facility_id, payload["reporter_phone_hash"])

    decision = gate_apply(result.records, settings.confidence_threshold, payload.get("lang", "en"))

    for record in decision.confirmed:
        live_store.put("stock_records", record.record_id, record)
        history_store.insert("stock_records", [record.model_dump(mode="json")])

    for record in decision.pending:
        live_store.put("stock_records", record.record_id, record)  # visible as pending, not silently dropped

    if decision.card is not None:
        messaging.send_buttons(payload["from"], decision.card.text, decision.card.buttons)
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
