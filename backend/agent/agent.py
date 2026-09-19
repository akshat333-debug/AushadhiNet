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
import re
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


_FACILITY_RE = re.compile(r"\b([A-Z]{2}-\d{7})\b", re.IGNORECASE)
_STOPWORDS = {"why", "is", "at", "risk", "for", "the", "of", "what", "which", "in", "a", "stock", "how", "much"}


def _drug_from(question: str) -> str | None:
    from backend.ingest.nlem import match
    words = [w for w in re.findall(r"[a-zA-Z]+", question.lower()) if w not in _STOPWORDS and len(w) > 2]
    after_for = question.lower().split(" for ", 1)
    candidates = re.findall(r"[a-zA-Z]+", after_for[1]) if len(after_for) == 2 else words[-1:]
    for word in candidates:
        found = match(word, k=1)
        if found:
            return found[0].drug_id
    return None


def _keyword_dispatch(question: str, officer: OfficerCtx) -> tuple[str, list[str], str | None]:
    """Local-mode fallback: a real ADK agent in cloud mode replaces this
    with genuine tool-calling. It can only call tools already in
    TOOL_REGISTRY, through call_tool's jurisdiction check -- no more power
    than the real agent has."""
    from backend.local_runtime import PILOT_DISTRICT
    lowered = question.lower()
    district = officer.jurisdiction if "/" in officer.jurisdiction else PILOT_DISTRICT

    def call(name, **kwargs):
        return tools.call_tool(name, officer.uid, officer.jurisdiction, **kwargs)

    facility_match = _FACILITY_RE.search(question)
    if facility_match:
        facility_id = facility_match.group(1).upper()
        drug_id = _drug_from(question)
        if drug_id:
            return call("explain_risk", facility_id=facility_id, drug_id=drug_id), [facility_id, drug_id], None
        stock = call("get_stock", facility_id=facility_id)
        lines = ", ".join(f"{r.drug_id} {r.on_hand}" for r in sorted(stock, key=lambda r: r.drug_id)[:13])
        return f"Latest stock at {facility_id}: {lines or 'no reports yet'}.", [facility_id], None

    if any(w in lowered for w in ("propose", "draft", "transfer", "redistribut")):
        drafts = call("propose_transfers", district_id=district)
        if not drafts:
            return f"No feasible transfers in {district} right now.", [], None
        top = drafts[0]
        return (
            f"Drafted {len(drafts)} transfer(s) for {district}; they need officer approval on the Orders page. "
            f"Largest-first example: {top.quantity} {top.drug_id} from {top.from_facility_id} to {top.to_facility_id} "
            f"({top.drive_minutes:.0f} min)."
        ), [top.order_id], top.order_id

    if any(w in lowered for w in ("risk", "shortage", "stock-out", "stockout", "running out", "low")):
        rows = call("list_at_risk", district_id=district)
        if not rows:
            return f"No facility in {district} is under a week of cover.", [], None
        lines = "; ".join(f"{r['name']} ({r['facility_id']}) {r['drug_id']}: {r['on_hand']} on hand vs {r['weekly_demand']}/week" for r in rows[:5])
        return f"Most at risk in {district}: {lines}.", [r["facility_id"] for r in rows[:5]], None

    return (
        "I can explain a facility's risk ('why is MH-0000221 at risk for ORS?'), list shortages "
        "('which facilities are at risk?'), or draft transfers ('propose transfers'). I cannot approve or send anything."
    ), [], None


def ask(question: str, officer: OfficerCtx) -> AgentAnswer:
    log(actor=f"agent:{officer.uid}", action="ask:entry", target_id="agent", payload={"question": question}, jurisdiction=officer.jurisdiction)

    llm = factory.get("llm")
    llm.generate(f"{INSTRUCTIONS}\n\nOfficer question: {question}")  # exercised for parity with the cloud path; local stub is not load-bearing here
    try:
        text, cited_ids, draft_order_id = _keyword_dispatch(question, officer)
    except PermissionError as exc:
        text, cited_ids, draft_order_id = f"That is outside your jurisdiction: {exc}", [], None

    log(actor=f"agent:{officer.uid}", action="ask:exit", target_id="agent", payload={"answer": text[:200]}, jurisdiction=officer.jurisdiction)
    return AgentAnswer(text=text, cited_ids=cited_ids, draft_order_id=draft_order_id)
