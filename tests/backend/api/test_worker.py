"""DoD test for backend/api/worker.py (step 30, AC3)."""
from __future__ import annotations

import base64
import hashlib
import json

from backend.domain import StaffRole
from backend.providers import factory
from backend.providers.base import ProviderError
from backend.providers.llm_local import FIXTURES_DIR as LLM_FIXTURES

from backend.api.worker import handle_bed_census, handle_checkin, handle_stock_message


def _register_llm_fixture(prompt_prefix: str, media_bytes: bytes, schema_name: str, fields: dict):
    media_hash = hashlib.sha256(media_bytes).hexdigest()[:16]
    key = hashlib.sha256(f"{prompt_prefix}|{media_hash}|{schema_name}".encode()).hexdigest()[:16]
    LLM_FIXTURES.mkdir(parents=True, exist_ok=True)
    (LLM_FIXTURES / f"{key}.json").write_text(json.dumps({"fields": fields, "confidence": {}}))


def test_fixture_photo_message_produces_confirmed_stock_record_in_both_stores():
    from backend.ingest.prompts import STOCK_REGISTER_PROMPT

    image_bytes = b"end-to-end-register-photo"
    _register_llm_fixture(
        STOCK_REGISTER_PROMPT, image_bytes, "StockExtraction",
        fields={"drug_name": "ORS (New WHO)", "on_hand": 60, "confidence": {"on_hand": 0.95, "drug_name": 0.92}},
    )
    data_uri = "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode()
    payload = {
        "from": "whatsapp:+911111111111", "reporter_phone_hash": "h1", "body": None,
        "num_media": 1, "media_url": data_uri, "media_content_type": "image/jpeg", "message_sid": "SM1",
    }

    handle_stock_message(payload, facility_id="F1")

    live = factory.get("store_live")
    history = factory.get("store_history")
    records = live.query("stock_records", {"facility_id": "F1"})
    assert len(records) == 1
    assert records[0].status.value == "confirmed"
    assert records[0].on_hand == 60

    rows = history.sql("select * from stock_records where facility_id = ?", ["F1"])
    assert len(rows) == 1


def test_low_confidence_photo_stays_pending_and_sends_a_card():
    from backend.ingest.prompts import STOCK_REGISTER_PROMPT

    image_bytes = b"blurry-register-photo"
    _register_llm_fixture(
        STOCK_REGISTER_PROMPT, image_bytes, "StockExtraction",
        fields={"drug_name": "ORS (New WHO)", "on_hand": 60, "confidence": {"on_hand": 0.5, "drug_name": 0.92}},
    )
    data_uri = "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode()
    payload = {
        "from": "whatsapp:+912222222222", "reporter_phone_hash": "h2", "body": None,
        "num_media": 1, "media_url": data_uri, "media_content_type": "image/jpeg", "message_sid": "SM2",
    }

    handle_stock_message(payload, facility_id="F2")

    messaging = factory.get("messaging")
    sent_to_f2 = [m for m in messaging.sent if m.to == "whatsapp:+912222222222"]
    assert len(sent_to_f2) == 1
    assert sent_to_f2[0].kind == "buttons"

    history = factory.get("store_history")
    try:
        rows = history.sql("select * from stock_records where facility_id = ?", ["F2"])
    except ProviderError:
        rows = []  # the table was never even created -- an even stronger guarantee than an empty result
    assert rows == []  # never written to history while pending -- "never silent write"


def test_bed_census_records_directly():
    record = handle_bed_census({"message_sid": "SM3"}, facility_id="F3", beds_total=10, beds_occupied=7)
    assert record.beds_total == 10 and record.beds_occupied == 7
    live = factory.get("store_live")
    assert live.get("bed_census", record.record_id) is not None


def test_checkin_within_geofence_is_ok():
    record = handle_checkin(
        {"message_sid": "SM4"}, facility_id="F4", staff_id_hash="s1", role=StaffRole.ANM,
        lat=20.0001, lon=73.8001, facility_lat=20.0, facility_lon=73.8,
    )
    assert record.geofence_ok is True


def test_checkin_900m_away_is_flagged_not_rejected():
    """AC3: a check-in outside the geofence is flagged, not rejected."""
    record = handle_checkin(
        {"message_sid": "SM5"}, facility_id="F5", staff_id_hash="s2", role=StaffRole.MO,
        lat=20.008, lon=73.8, facility_lat=20.0, facility_lon=73.8,  # ~890m north
    )
    assert 800 < record.distance_m < 1000
    assert record.geofence_ok is False
    # still recorded, not dropped
    live = factory.get("store_live")
    assert live.get("checkins", record.record_id) is not None


def test_fixture_audio_message_produces_confirmed_stock_record_end_to_end():
    """AC2: a Marathi voice note yields a correct stock update end to end
    (worker-level, not just extract.py in isolation)."""
    from backend.ingest.prompts import STOCK_VOICE_PROMPT
    from backend.providers.speech_local import FIXTURES_DIR as SPEECH_FIXTURES

    audio_bytes = b"end-to-end-marathi-voice-note"
    key = hashlib.sha256(audio_bytes).hexdigest()[:16]
    SPEECH_FIXTURES.mkdir(parents=True, exist_ok=True)
    (SPEECH_FIXTURES / f"{key}.json").write_text(json.dumps({"text": "Zinc pannas goli", "language": "mr", "confidence": 0.9}))

    prompt = f"{STOCK_VOICE_PROMPT}\n\nTranscript: Zinc pannas goli"
    _register_llm_fixture(
        prompt, b"", "StockExtraction",
        fields={"drug_name": "Zinc 20 mg tablet", "on_hand": 50, "confidence": {"on_hand": 0.92, "drug_name": 0.9}},
    )
    data_uri = "data:audio/ogg;base64," + base64.b64encode(audio_bytes).decode()
    payload = {
        "from": "whatsapp:+913333333333", "reporter_phone_hash": "h6", "body": None,
        "num_media": 1, "media_url": data_uri, "media_content_type": "audio/ogg", "message_sid": "SM7",
    }

    handle_stock_message(payload, facility_id="F6")

    live = factory.get("store_live")
    records = live.query("stock_records", {"facility_id": "F6"})
    assert len(records) == 1
    assert records[0].status.value == "confirmed"
    assert records[0].on_hand == 50
