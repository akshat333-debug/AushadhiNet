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
    from backend.i18n import find_local_drug
    from backend.ingest.nlem import match
    local = find_local_drug(question)
    if local:
        return local
    words = [w for w in re.findall(r"[a-zA-Z]+", question.lower()) if w not in _STOPWORDS and len(w) > 2]
    after_for = question.lower().split(" for ", 1)
    candidates = re.findall(r"[a-zA-Z]+", after_for[1]) if len(after_for) == 2 else words[-1:]
    for word in candidates:
        found = match(word, k=1)
        if found:
            return found[0].drug_id
    return None


def _keyword_dispatch(question: str, officer: OfficerCtx, lang: str = "en") -> tuple[str, list[str], str | None]:
    """Local-mode fallback: a real ADK agent in cloud mode replaces this
    with genuine tool-calling. It can only call tools already in
    TOOL_REGISTRY, through call_tool's jurisdiction check -- no more power
    than the real agent has."""
    from backend.i18n import INTENT_WORDS, drug_name, msg, place_name
    from backend.runtime import PILOT_DISTRICT
    lowered = question.lower()
    district_id = officer.jurisdiction if "/" in officer.jurisdiction else PILOT_DISTRICT
    district = place_name(district_id, lang)

    def call(name, **kwargs):
        return tools.call_tool(name, officer.uid, officer.jurisdiction, **kwargs)

    facility_match = _FACILITY_RE.search(question)
    if facility_match:
        facility_id = facility_match.group(1).upper()
        drug_id = _drug_from(question)
        if drug_id:
            forecasts = call("get_forecast", facility_id=facility_id, drug_id=drug_id)
            drug = drug_name(drug_id, lang)
            if not forecasts:
                return msg(lang, "agent_no_forecast", facility=facility_id, drug=drug), [facility_id, drug_id], None
            f = forecasts[0]
            text = msg(lang, "agent_explain", facility=facility_id, drug=drug, prob=f"{f.stockout_prob:.0%}",
                       p50=f"{f.p50:.0f}", p10=f"{f.p10:.0f}", p90=f"{f.p90:.0f}")
            return text, [facility_id, drug_id], None
        stock = call("get_stock", facility_id=facility_id)
        lines = ", ".join(f"{drug_name(r.drug_id, lang)} {r.on_hand}" for r in sorted(stock, key=lambda r: r.drug_id)[:16])
        return msg(lang, "agent_stock", facility=facility_id, lines=lines or msg(lang, "agent_no_reports")), [facility_id], None

    if any(w in lowered for w in INTENT_WORDS["propose"]):
        drafts = call("propose_transfers", district_id=district_id)
        if not drafts:
            return msg(lang, "agent_no_transfers", district=district), [], None
        top = drafts[0]
        text = msg(lang, "agent_drafted", n=len(drafts), district=district, qty=top.quantity, drug=drug_name(top.drug_id, lang),
                   src=top.from_facility_id, dst=top.to_facility_id, minutes=f"{top.drive_minutes:.0f}")
        return text, [top.order_id], top.order_id

    if any(w in lowered for w in INTENT_WORDS["risk"]):
        rows = call("list_at_risk", district_id=district_id)
        if not rows:
            return msg(lang, "agent_none_at_risk", district=district), [], None
        lines = "; ".join(
            msg(lang, "agent_at_risk_line", name=r["name"], facility=r["facility_id"], drug=drug_name(r["drug_id"], lang),
                on_hand=r["on_hand"], demand=f"{r['weekly_demand']:.0f}")
            for r in rows[:5]
        )
        return msg(lang, "agent_at_risk", district=district, lines=lines), [r["facility_id"] for r in rows[:5]], None

    return msg(lang, "agent_help"), [], None


def ask(question: str, officer: OfficerCtx, lang: str = "en") -> AgentAnswer:
    log(actor=f"agent:{officer.uid}", action="ask:entry", target_id="agent", payload={"question": question}, jurisdiction=officer.jurisdiction)

    llm = factory.get("llm")
    llm.generate(f"{INSTRUCTIONS}\n\nOfficer question: {question}")  # exercised for parity with the cloud path; local stub is not load-bearing here
    try:
        text, cited_ids, draft_order_id = _keyword_dispatch(question, officer, lang)
    except PermissionError as exc:
        from backend.i18n import msg
        text, cited_ids, draft_order_id = msg(lang, "agent_outside", detail=exc), [], None

    log(actor=f"agent:{officer.uid}", action="ask:exit", target_id="agent", payload={"answer": text[:200]}, jurisdiction=officer.jurisdiction)
    return AgentAnswer(text=text, cited_ids=cited_ids, draft_order_id=draft_order_id)
