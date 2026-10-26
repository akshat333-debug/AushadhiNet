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
