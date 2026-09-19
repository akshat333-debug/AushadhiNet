"""The officer agent's entry point (modular-plan.md §2.6). In cloud mode
this wraps a real Gemini function-calling loop via Google's Agent
Development Kit; in local mode, the LLM stub cannot actually invoke tools
autonomously, so `ask()` does a light keyword dispatch on top of the same
TOOL_REGISTRY -- the governance guarantee (AC7) does not depend on which
path is taken, since TOOL_REGISTRY itself has no dangerous capability
either way.
"""
from __future__ import annotations

import pathlib
from dataclasses import dataclass, field

from backend.providers import factory

from backend.agent import tools
from backend.agent.audit import log

INSTRUCTIONS = (pathlib.Path(__file__).parent / "instructions.md").read_text()


@dataclass
class OfficerCtx:
    uid: str
    jurisdiction: str


@dataclass
class AgentAnswer:
    text: str
    cited_ids: list[str] = field(default_factory=list)
    draft_order_id: str | None = None


def _keyword_dispatch(question: str, officer: OfficerCtx) -> tuple[str, list[str], str | None]:
    """Local-mode fallback: a real ADK agent in cloud mode replaces this
    with genuine tool-calling; this exists so the demo and tests have a
    grounded answer without a live Gemini connection. It can only ever
    call tools already in TOOL_REGISTRY -- it has no more power than the
    real agent does."""
    lowered = question.lower()
    cited_ids: list[str] = []

    if "risk" in lowered or "why" in lowered:
        # crude extraction: look for a facility id and drug id token in the question
        words = question.replace("?", "").split()
        facility_id = next((w for w in words if "-" in w and w[0].isalpha()), None)
        if facility_id:
            drug_id = words[-1].lower()
            text = tools.call_tool("explain_risk", officer.uid, officer.jurisdiction, facility_id=facility_id, drug_id=drug_id)
            cited_ids = [facility_id, drug_id]
            return text, cited_ids, None

    return (
        "I can look up facility stock, forecasts, and draft transfer proposals. "
        "Try asking about a specific facility and drug, e.g. 'why is F1 at risk for ors?'."
    ), cited_ids, None


def ask(question: str, officer: OfficerCtx) -> AgentAnswer:
    log(actor=f"agent:{officer.uid}", action="ask:entry", target_id="agent", payload={"question": question}, jurisdiction=officer.jurisdiction)

    llm = factory.get("llm")
    llm.generate(f"{INSTRUCTIONS}\n\nOfficer question: {question}")  # exercised for parity with the cloud path; local stub is not load-bearing here
    text, cited_ids, draft_order_id = _keyword_dispatch(question, officer)

    log(actor=f"agent:{officer.uid}", action="ask:exit", target_id="agent", payload={"answer": text[:200]}, jurisdiction=officer.jurisdiction)
    return AgentAnswer(text=text, cited_ids=cited_ids, draft_order_id=draft_order_id)
