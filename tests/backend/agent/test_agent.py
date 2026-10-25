

def test_gemini_note_is_added_only_when_it_adds_no_numbers_or_actions(monkeypatch):
    from backend.agent import agent as agent_mod
    from backend.providers.base import LLMResponse

    monkeypatch.setattr("backend.config.get_settings", lambda: type("S", (), {"mode": "cloud"})())
    answers = iter([
        "Stock will not last the week; check the delivery date.",
        "Expect 999 units short.",          # invents a number
        "You should approve a transfer.",   # talks about acting
    ])
    monkeypatch.setattr(agent_mod.factory, "get", lambda name: type("L", (), {"generate": lambda self, p, **kw: LLMResponse(text=next(answers), tool_calls=[])})())
    base = "MH-0000221 ORS: 3 on hand, 12 expected next week."
    assert agent_mod._with_gemini_note(base, "why?", "en").endswith("check the delivery date.")
    assert agent_mod._with_gemini_note(base, "why?", "en") == base
    assert agent_mod._with_gemini_note(base, "why?", "en") == base
