"""Gemini function calling for questions the templates don't cover, with a fake Gemini that
calls the declared functions the way the real one does."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app

OFFICER = {"Authorization": "Bearer dev:o1:district:mh/nashik"}
QUESTION = "Compare what Dindori and Nandgaon hold"


class FakeGemini:
    def __init__(self, script):
        self.script, self.results = script, []

    def run_tools(self, system, question, declarations, call, **_):
        assert {d["name"] for d in declarations} >= {"find_facility", "facility_stock", "capacity"}
        assert not any(w in d["name"] for d in declarations for w in ("approve", "send", "sign"))
        return self.script(call, self.results)


@pytest.fixture
def cloud_agent(monkeypatch):
    import backend.agent.agent as agent
    monkeypatch.setattr(agent, "_cloud", lambda: True)
    monkeypatch.setattr(agent, "_with_gemini_note", lambda text, *_: text)

    def use(script):
        fake = FakeGemini(script)
        monkeypatch.setattr(agent, "_llm", lambda: fake)
        return fake
    return use


def _ask(client, question=QUESTION):
    return client.post("/agent/ask", json={"question": question}, headers=OFFICER).json()


def test_gemini_answers_from_what_its_functions_returned(cloud_agent):
    def script(call, results):
        found = call("find_facility", {"name": "Dindori"})
        stock = call("facility_stock", {"facility_id": found[0]["facility_id"]})
        results.append(stock)
        top = max(stock, key=lambda r: r["on_hand"])
        return f"{found[0]['name']} ({found[0]['facility_id']}) holds the most {top['medicine']}: {top['on_hand']} units."
    with TestClient(create_app()) as client:
        cloud_agent(script)
        answer = _ask(client)
    assert answer["text"].startswith("Dindori (MH-0000301) holds the most") and answer["cited_ids"] == ["MH-0000301"]


def test_an_invented_number_drops_the_answer(cloud_agent):
    with TestClient(create_app()) as client:
        cloud_agent(lambda call, _: (call("capacity", {}), "Nashik has 98765 beds free.")[1])
        assert _ask(client)["text"].startswith("I can explain a facility's risk")


def test_functions_stay_inside_the_officers_jurisdiction(cloud_agent):
    seen = []
    with TestClient(create_app()) as client:
        cloud_agent(lambda call, _: (seen.append(call("facility_stock", {"facility_id": "MH-0000337"})), "Dhule is not yours.")[1])
        _ask(client)
    assert "outside your jurisdiction" in seen[0]["error"]


def test_requests_to_act_never_reach_gemini(cloud_agent):
    with TestClient(create_app()) as client:
        cloud_agent(lambda call, _: pytest.fail("Gemini must not see this"))
        assert "I cannot approve or send anything" in _ask(client, "please approve all drafts for me")["text"]


def test_a_number_only_the_officer_typed_is_not_grounded(cloud_agent):
    """Judge's case: "Are there 999 units available?" answered "There are 999 units" with no function call."""
    with TestClient(create_app()) as client:
        cloud_agent(lambda call, _: "There are 999 units available.")
        assert _ask(client, "Compare: are there 999 units available?")["text"].startswith("I can explain a facility's risk")


def test_current_stock_is_the_latest_confirmed_count_only():
    """Judge's case: yesterday's 100 and a pending 999 must not appear beside today's 20."""
    from datetime import datetime, timedelta, timezone
    from backend.agent.tools import get_stock
    from backend.domain import Confidence, ConfidenceSource, RecordStatus, StockRecord
    from backend.providers import factory
    from backend.runtime import latest_records, note_confirmed
    with TestClient(create_app()):
        latest_records()
        now = datetime.now(timezone.utc)
        for rid, on_hand, status, at in (("y", 100, RecordStatus.CONFIRMED, now - timedelta(days=1)),
                                          ("t", 20, RecordStatus.CONFIRMED, now), ("p", 999, RecordStatus.PENDING, now)):
            r = StockRecord(record_id=rid, facility_id="MH-0000221", drug_id="ors", reported_at=at, as_of_date=at.date(),
                            on_hand=on_hand, status=status, reporter_phone_hash="h", raw_message_id=rid,
                            confidence=Confidence(field_confidence={"on_hand": 1.0}, overall=1.0, source=ConfidenceSource.MANUAL))
            factory.get("store_live").put("stock_records", rid, r)
            if status == RecordStatus.CONFIRMED:
                note_confirmed(r)
        assert [r.on_hand for r in get_stock("MH-0000221", "ors")] == [20]


def test_a_difference_of_two_returned_numbers_is_grounded(cloud_agent):
    def script(call, results):
        found = call("find_facility", {"name": "Dindori"})
        stock = sorted(call("facility_stock", {"facility_id": found[0]["facility_id"]}), key=lambda r: -r["on_hand"])
        a, b = stock[0]["on_hand"], stock[1]["on_hand"]
        return f"{stock[0]['medicine']} {a} and {stock[1]['medicine']} {b}: a difference of {a - b}."
    with TestClient(create_app()) as client:
        cloud_agent(script)
        assert "a difference of" in _ask(client)["text"]


def test_a_facilitys_beds_question_is_not_answered_with_its_medicine_stock(cloud_agent):
    with TestClient(create_app()) as client:
        cloud_agent(lambda call, _: (call("capacity", {}), "Sinnar Phata is not on today's full list.")[1])
        assert _ask(client, "Does Sinnar Phata have full beds today?")["text"] == "Sinnar Phata is not on today's full list."


def test_capacity_for_one_facility_is_not_cut_to_the_district_top_ten(cloud_agent):
    def script(call, results):
        found = call("find_facility", {"name": "Sinnar Phata"})
        cap = call("capacity", {"facility_id": found[0]["facility_id"]})
        results.append(cap)
        return f"{found[0]['name']} has its numbers." if "facility" in cap else "missing"
    with TestClient(create_app()) as client:
        fake = cloud_agent(script)
        assert _ask(client, "Compare beds at Sinnar Phata")["text"].endswith("has its numbers.")
        assert fake.results[0]["facility"]["posts"]


def test_a_facility_name_in_place_of_an_id_still_resolves(cloud_agent):
    def script(call, results):
        results.append(call("capacity", {"facility_id": "Sinnar Phata"}))
        return "Sinnar Phata has its numbers."
    with TestClient(create_app()) as client:
        fake = cloud_agent(script)
        _ask(client, "Compare beds at Sinnar Phata")
    assert fake.results[0]["facility"]["posts"] and "beds" not in fake.results[0]  # no district totals beside it
