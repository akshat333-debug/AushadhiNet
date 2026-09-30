"""Multilingual behaviour: native-script reports, localized replies, cards and agent answers."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.i18n import DRUG_NAMES, LANGS, MESSAGES
from backend.ingest.parse_text import from_text

PHONE = "whatsapp:+919800000221"


def test_every_language_has_every_message_and_drug_name():
    for lang in LANGS:
        assert set(MESSAGES[lang]) == set(MESSAGES["en"]), lang
    for names in DRUG_NAMES.values():
        assert set(names) == set(LANGS)


@pytest.mark.parametrize("body, drug, qty", [
    ("ओआरएस 50", "ors", 50),          # Marathi/Hindi script
    ("झिंक ५", "zinc-20mg", 5),        # Devanagari digits, unambiguous first word
    ("ஓஆர்எஸ் 7", "ors", 7),           # Tamil
    ("কালসিয়াম 2", None, 2),          # misspelt Bengali: parsed, but not trusted
])
def test_native_script_reports_parse(body, drug, qty):
    record = from_text(body, "F1", "h").records[0]
    assert record.on_hand == qty
    if drug:
        assert record.drug_id == drug and record.confidence.overall == 1.0
    else:
        assert record.confidence.overall < 0.85


def test_ambiguous_ifa_is_not_trusted():
    record = from_text("आयएफए 4", "F1", "h").records[0]
    assert record.confidence.overall < 0.85  # four IFA products; must go to a confirmation card


def test_replies_follow_the_message_language():
    with TestClient(create_app()) as client:
        client.post("/simulator/message", json={"from_phone": PHONE, "body": "ओआरएस 50", "message_id": "a", "lang": "mr"})
        client.post("/simulator/message", json={"from_phone": PHONE, "body": "IFA 20", "message_id": "b", "lang": "ta"})
        client.post("/simulator/message", json={"from_phone": PHONE, "body": "हो", "message_id": "c", "lang": "mr"})
        outbox = client.get("/simulator/outbox", params={"phone": PHONE}).json()
        assert outbox[0]["body"] == "MH-0000221 साठी नोंद केली: ओआरएस 50."
        assert outbox[1]["buttons"] == ["உறுதிப்படுத்து", "திருத்து"]
        assert outbox[2]["body"] == "1 नोंद(दी) निश्चित केल्या."


def test_agent_answers_in_the_requested_language():
    headers = {"Authorization": "Bearer dev:o1:district:mh/nashik"}
    with TestClient(create_app()) as client:
        answer = client.post("/agent/ask", json={"question": "MH-0000221 मध्ये ओआरएसचा धोका का आहे?", "lang": "mr"}, headers=headers).json()
        assert answer["cited_ids"] == ["MH-0000221", "ors"]
        assert "पुढील आठवड्यात संपण्याची शक्यता" in answer["text"]


def test_drug_names_endpoint_and_facility_coordinates():
    with TestClient(create_app()) as client:
        assert client.get("/public/drug-names").json()["ors"]["mr"] == "ओआरएस"
        facilities = client.get("/officer/districts/mh/nashik/facilities", headers={"Authorization": "Bearer dev:o1:district:mh/nashik"}).json()
        assert all(19 < f["lat"] < 21.5 and 73 < f["lon"] < 75.5 for f in facilities)


def test_public_facility_points_carry_no_identifiers():
    with TestClient(create_app()) as client:
        points = client.get("/public/facility-points").json()
        assert len(points) == 760 and all(len(p) == 2 for p in points)
        assert "MH-" not in client.get("/public/facility-points").text
