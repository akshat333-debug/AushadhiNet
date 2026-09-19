"""DoD test for backend/providers/ (step 25): the same contract assertions
run against every local implementation, and every protocol must have both
a local and a (real, importable) google class.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from backend.providers.base import Media, ProviderError
from backend.providers.embed_local import LocalEmbedProvider
from backend.providers.llm_local import LocalLLMProvider
from backend.providers.messaging_local import LocalMessaging
from backend.providers.queue_local import LocalQueue
from backend.providers.routes_local import LocalRouteProvider
from backend.providers.sign_local import LocalSigner
from backend.providers.speech_local import FIXTURES_DIR as SPEECH_FIXTURES, LocalSpeechProvider
from backend.providers.store_history_local import LocalHistoryStore
from backend.providers.store_live_local import LocalLiveStore
from backend.providers.translate_local import LocalTranslateProvider
from backend.providers.tts_local import LocalTTSProvider


# --- speech ---

def test_speech_raises_provider_error_on_unknown_audio():
    with pytest.raises(ProviderError):
        LocalSpeechProvider().transcribe(b"unregistered-audio-bytes", "audio/ogg")


def test_speech_returns_fixture_transcript(tmp_path, monkeypatch):
    import backend.providers.speech_local as mod
    monkeypatch.setattr(mod, "FIXTURES_DIR", tmp_path)
    audio = b"hello"
    key = __import__("hashlib").sha256(audio).hexdigest()[:16]
    (tmp_path / f"{key}.json").write_text(json.dumps({"text": "5 ORS", "language": "mr", "confidence": 0.9}))
    t = mod.LocalSpeechProvider().transcribe(audio, "audio/ogg")
    assert t.text == "5 ORS" and t.language == "mr"


# --- llm ---

def test_llm_extract_raises_on_unknown_fixture():
    from pydantic import BaseModel

    class Schema(BaseModel):
        x: int

    with pytest.raises(ProviderError):
        LocalLLMProvider().extract("prompt", [Media(data=b"img", mime="image/jpeg")], Schema)


def test_llm_generate_returns_response_without_network():
    resp = LocalLLMProvider().generate("hello agent")
    assert resp.text
    assert resp.tool_calls == []


# --- embed ---

def test_embed_returns_correct_shape_and_is_deterministic():
    e = LocalEmbedProvider()
    v1 = e.embed(["ORS", "Zinc"])
    v2 = e.embed(["ORS", "Zinc"])
    assert v1.shape == (2, 256)
    np.testing.assert_array_equal(v1, v2)


def test_embed_similar_strings_are_closer_than_dissimilar():
    e = LocalEmbedProvider()
    v = e.embed(["Paracetamol 500mg", "Paracetamol 650mg", "Zinc sulphate"])
    sim_close = v[0] @ v[1]
    sim_far = v[0] @ v[2]
    assert sim_close > sim_far


# --- translate / tts ---

def test_translate_tags_non_english():
    t = LocalTranslateProvider()
    assert t.translate("hello", "mr") == "[mr] hello"
    assert t.translate("hello", "en") == "hello"


def test_tts_returns_bytes():
    audio = LocalTTSProvider().synthesize("hello", "mr")
    assert isinstance(audio, bytes) and len(audio) > 0


# --- store_live ---

def test_live_store_put_get_query():
    from pydantic import BaseModel

    class Doc(BaseModel):
        name: str
        status: str

    store = LocalLiveStore()
    store.put("facilities", "F1", Doc(name="PHC A", status="active"))
    assert store.get("facilities", "F1").name == "PHC A"
    assert len(store.query("facilities", {"status": "active"})) == 1


def test_live_store_watch_fires_on_put():
    from pydantic import BaseModel

    class Doc(BaseModel):
        name: str

    store = LocalLiveStore()
    seen = []
    unsub = store.watch("facilities", lambda doc_id, doc: seen.append((doc_id, doc.name)))
    store.put("facilities", "F1", Doc(name="PHC A"))
    assert seen == [("F1", "PHC A")]
    unsub()
    store.put("facilities", "F2", Doc(name="PHC B"))
    assert len(seen) == 1  # no longer watching


# --- store_history ---

def test_history_store_insert_and_parameterised_query():
    store = LocalHistoryStore(":memory:")
    store.insert("stock", [{"facility_id": "F1", "qty": 10}, {"facility_id": "F2", "qty": 20}])
    rows = store.sql("select * from stock where qty > ?", [15])
    assert len(rows) == 1 and rows[0]["facility_id"] == "F2"


def test_history_store_raises_provider_error_on_bad_sql():
    store = LocalHistoryStore(":memory:")
    with pytest.raises(ProviderError):
        store.sql("select * from a_table_that_does_not_exist")


# --- queue ---

def test_queue_publish_calls_subscriber():
    q = LocalQueue()
    received = []
    q.subscribe("stock.updates", lambda payload: received.append(payload))
    q.publish("stock.updates", {"facility_id": "F1"})
    assert received == [{"facility_id": "F1"}]


# --- sign ---

def test_signer_verifies_own_signature():
    s = LocalSigner("test-key")
    sig = s.sign(b"order-payload")
    assert s.verify(b"order-payload", sig)
    assert not s.verify(b"tampered-payload", sig)


# --- messaging ---

def test_messaging_logs_sent_messages():
    m = LocalMessaging()
    m.send_text("+911234567890", "hello")
    m.send_buttons("+911234567890", "confirm?", ["yes", "no"])
    assert len(m.sent) == 2
    assert m.sent[1].extra["buttons"] == ["yes", "no"]


# --- routes ---

def test_route_provider_matches_haversine_contract():
    from backend.domain import Facility, FacilityType

    a = Facility(facility_id="F1", name="A", state_code="MH", district_id="mh/nashik",
                  facility_type=FacilityType.PHC, lat=20.0, lon=73.8)
    b = Facility(facility_id="F2", name="B", state_code="MH", district_id="mh/nashik",
                  facility_type=FacilityType.PHC, lat=20.1, lon=73.9)
    minutes = LocalRouteProvider().drive_minutes(a, b)
    assert minutes > 0


# --- every protocol has both a local and a real, importable google module ---

@pytest.mark.parametrize("provider_name,local_module,local_class,google_module,google_class", [
    ("speech", "speech_local", "LocalSpeechProvider", "speech_google", "GoogleSpeechProvider"),
    ("llm", "llm_local", "LocalLLMProvider", "llm_google", "GoogleLLMProvider"),
    ("embed", "embed_local", "LocalEmbedProvider", "embed_google", "GoogleEmbedProvider"),
    ("translate", "translate_local", "LocalTranslateProvider", "translate_google", "GoogleTranslateProvider"),
    ("tts", "tts_local", "LocalTTSProvider", "tts_google", "GoogleTTSProvider"),
    ("store_live", "store_live_local", "LocalLiveStore", "store_live_google", "GoogleLiveStore"),
    ("store_history", "store_history_local", "LocalHistoryStore", "store_history_google", "GoogleHistoryStore"),
    ("queue", "queue_local", "LocalQueue", "queue_google", "GooglePubSubQueue"),
    ("sign", "sign_local", "LocalSigner", "sign_google", "GoogleKMSSigner"),
    ("messaging", "messaging_local", "LocalMessaging", "messaging_google", "TwilioMessaging"),
    ("routes", "routes_local", "LocalRouteProvider", "routes_google", "GoogleRouteProvider"),
])
def test_both_implementations_exist(provider_name, local_module, local_class, google_module, google_class):
    import importlib
    local_mod = importlib.import_module(f"backend.providers.{local_module}")
    assert hasattr(local_mod, local_class)
    google_mod = importlib.import_module(f"backend.providers.{google_module}")
    assert hasattr(google_mod, google_class)
