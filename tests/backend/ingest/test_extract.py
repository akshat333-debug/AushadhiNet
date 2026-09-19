"""DoD test for backend/ingest/extract.py + parse_text.py (step 27, AC1/AC2)."""
from __future__ import annotations

import json

import pytest

from backend.ingest.extract import from_audio, from_image
from backend.ingest.parse_text import from_text
from backend.providers.base import ProviderError
from backend.providers.llm_local import FIXTURES_DIR as LLM_FIXTURES
from backend.providers.speech_local import FIXTURES_DIR as SPEECH_FIXTURES


def _register_llm_fixture(prompt_prefix: str, media_bytes: bytes, schema_name: str, fields: dict, confidence: dict):
    import hashlib
    media_hash = hashlib.sha256(media_bytes).hexdigest()[:16] if media_bytes else hashlib.sha256(b"").hexdigest()[:16]
    key = hashlib.sha256(f"{prompt_prefix}|{media_hash}|{schema_name}".encode()).hexdigest()[:16]
    LLM_FIXTURES.mkdir(parents=True, exist_ok=True)
    (LLM_FIXTURES / f"{key}.json").write_text(json.dumps({"fields": fields, "confidence": confidence}))


def test_from_image_hindi_style_register_yields_expected_row(monkeypatch):
    from backend.ingest.prompts import STOCK_REGISTER_PROMPT

    image_bytes = b"fake-register-photo-bytes"
    _register_llm_fixture(
        STOCK_REGISTER_PROMPT, image_bytes, "StockExtraction",
        fields={"drug_name": "ORS (New WHO)", "on_hand": 42, "confidence": {"on_hand": 0.95, "drug_name": 0.9}},
        confidence={},
    )
    result = from_image(image_bytes, "image/jpeg", facility_id="F1", reporter_phone_hash="h1")
    assert len(result.records) == 1
    assert result.records[0].on_hand == 42
    assert result.records[0].drug_id  # normalised via NLEM match


def test_from_audio_marathi_voice_note_yields_expected_row(monkeypatch):
    from backend.ingest.prompts import STOCK_VOICE_PROMPT

    audio_bytes = b"fake-marathi-voice-note"
    key = __import__("hashlib").sha256(audio_bytes).hexdigest()[:16]
    SPEECH_FIXTURES.mkdir(parents=True, exist_ok=True)
    (SPEECH_FIXTURES / f"{key}.json").write_text(json.dumps({"text": "Zinc pannas goli", "language": "mr", "confidence": 0.85}))

    prompt = f"{STOCK_VOICE_PROMPT}\n\nTranscript: Zinc pannas goli"
    _register_llm_fixture(
        prompt, b"", "StockExtraction",
        fields={"drug_name": "Zinc 20 mg tablet", "on_hand": 50, "confidence": {"on_hand": 0.8, "drug_name": 0.9}},
        confidence={},
    )
    result = from_audio(audio_bytes, "audio/ogg", facility_id="F1", reporter_phone_hash="h1", lang_hint="mr-IN")
    assert result.transcript == "Zinc pannas goli"
    assert result.records[0].on_hand == 50


def test_from_audio_raises_provider_error_on_unregistered_fixture():
    with pytest.raises(ProviderError):
        from_audio(b"totally-unregistered-audio", "audio/ogg", facility_id="F1", reporter_phone_hash="h1")


# --- parse_text (English text update, part of AC1's channel set) ---

def test_from_text_parses_simple_drug_quantity_line():
    result = from_text("ORS 50", facility_id="F1", reporter_phone_hash="h1")
    assert len(result.records) == 1
    assert result.records[0].on_hand == 50
    assert result.records[0].confidence.overall == 1.0


def test_from_text_parses_multiple_lines():
    result = from_text("ORS 50\nZinc 20mg tablet: 30", facility_id="F1", reporter_phone_hash="h1")
    assert len(result.records) == 2
    assert {r.on_hand for r in result.records} == {50, 30}


def test_from_text_ignores_unparseable_lines():
    result = from_text("hello there\nORS 50\nhow are you", facility_id="F1", reporter_phone_hash="h1")
    assert len(result.records) == 1


def test_from_text_no_records_gives_zero_confidence():
    result = from_text("just chatting, no numbers here", facility_id="F1", reporter_phone_hash="h1")
    assert result.records == []
    assert result.confidence.overall == 0.0
