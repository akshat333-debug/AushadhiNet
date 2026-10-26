"""The officer agent's entry point (modular-plan.md §2.6). Three paths, in order:
1. A request to approve, send or execute is refused before any model sees it.
2. Questions the demo and officers ask most (a facility's risk, by name or ID; who is at risk;
   propose transfers; beds and staff) are answered by fixed templates over TOOL_REGISTRY, fast and
   always phrased the same; in cloud mode Gemini adds a guarded note.
3. Anything else goes to Gemini function calling (cloud mode): Gemini picks from the declared
   read-only functions, each run through call_tool's jurisdiction check, and its answer is dropped
   if it states a number no tool returned. Locally, or if Gemini fails, the officer gets the help text.
AC7 does not depend on the path: no declared function can approve, sign or send.
"""
from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass, field

import logging

from backend.providers import factory

from backend.agent import tools
from backend.agent.audit import log

_log = logging.getLogger(__name__)
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


_FACILITY_RE = re.compile(r"\b([A-Z]{2,3}-\d{7})\b", re.IGNORECASE)


def _facility_in(question: str, district_id: str) -> str | None:
    """A facility ID, or the longest facility name in the officer's district that the question
    mentions ("Why is Nandgaon at risk for ORS?")."""
    found = _FACILITY_RE.search(question)
    if found:
        return found.group(1).upper()
    from backend.agent.tools import find_facility
    lowered = f" {' '.join(re.findall(r'[\w.]+', question.lower()))} "
    from ml.data.facilities import served_facility_index
    # The officer's own district first; then the rest, so asking about another district's facility
    # reaches the tool layer's jurisdiction check and is refused, rather than silently unmatched.
    others = sorted({f.district_id for f in served_facility_index().values()} - {district_id})
    for district in [district_id, *others]:
        names = _district_names(district)
        hits = [variant for variant in names if f" {variant} " in lowered]
        if hits:
            best = find_facility(names[max(hits, key=len)], district)
            return best[0]["facility_id"] if best else None
    return None


_names_cache: dict[str, dict[str, str]] = {}
_COMPARE_WORDS = ("compare", " vs ", "versus", "difference between", "तुलना", "तुलना करा", "তুলনা", "ஒப்பிடு", "పోల్చ", "ಹೋಲಿಸ")


def _district_names(district_id: str) -> dict[str, str]:
    """Spoken variant -> directory name. Officers drop an all-caps organisation prefix
    ("Sinnar Phata" for "NSKMC Sinnar Phata")."""
    if district_id not in _names_cache:
        from ml.data.facilities import served_facility_index
        variants: dict[str, str] = {}
        for f in served_facility_index().values():
            if f.district_id != district_id:
                continue
            words = re.findall(r"[\w.]+", f.name)
            for start in (0, 1 if len(words) > 1 and words[0].isupper() and len(words[0]) > 2 else 0):
                key = " ".join(words[start:]).lower()
                if len(key) > 3:
                    variants.setdefault(key, f.name)
        _names_cache[district_id] = variants
    return _names_cache[district_id]
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
        if found and found[0].score >= 0.8:  # "have" fuzzily matched ribavirin at 0.33
            return found[0].drug_id
    return None


def _keyword_dispatch(question: str, officer: OfficerCtx, lang: str = "en") -> tuple[str, list[str], str | None] | None:
    """Fixed templates for the common questions; None when none fits. Only calls tools in
    TOOL_REGISTRY, through call_tool's jurisdiction check."""
    from backend.i18n import INTENT_WORDS, drug_name, msg, place_name
    from backend.runtime import PILOT_DISTRICT
    lowered = question.lower()
    district_id = officer.jurisdiction if "/" in officer.jurisdiction else PILOT_DISTRICT
    district = place_name(district_id, lang)

    def call(name, **kwargs):
        return tools.call_tool(name, officer.uid, officer.jurisdiction, **kwargs)

    # Comparisons and questions about several facilities need reasoning across tools: Gemini's job.
    named = {v for v in _district_names(district_id) if f" {v} " in f" {' '.join(re.findall(r'[\w.]+', lowered))} "}
    if len(named) > 1 or any(w in lowered for w in _COMPARE_WORDS):
        return None

    facility_id = _facility_in(question, district_id)
    if facility_id:
        from ml.data.facilities import served_facility_index
        known = served_facility_index().get(facility_id)
        label = f"{known.name} ({facility_id})" if known else facility_id
        drug_id = _drug_from(question)
        if drug_id:
            forecasts = call("get_forecast", facility_id=facility_id, drug_id=drug_id)
            drug = drug_name(drug_id, lang)
            if not forecasts:
                return msg(lang, "agent_no_forecast", facility=label, drug=drug), [facility_id, drug_id], None
            f = forecasts[0]
            text = msg(lang, "agent_explain", facility=label, drug=drug, prob=f"{f.stockout_prob:.0%}",
                       p50=f"{f.p50:.0f}", p10=f"{f.p10:.0f}", p90=f"{f.p90:.0f}")
            return text, [facility_id, drug_id], None
        stock = call("get_stock", facility_id=facility_id)
        lines = ", ".join(f"{drug_name(r.drug_id, lang)} {r.on_hand}" for r in sorted(stock, key=lambda r: r.drug_id)[:16])
        return msg(lang, "agent_stock", facility=label, lines=lines or msg(lang, "agent_no_reports")), [facility_id], None

    if any(w in lowered for w in INTENT_WORDS["propose"]):
        drafts = call("propose_transfers", district_id=district_id)
        if not drafts:
            return msg(lang, "agent_no_transfers", district=district), [], None
        top = drafts[0]
        text = msg(lang, "agent_drafted", n=len(drafts), district=district, qty=top.quantity, drug=drug_name(top.drug_id, lang),
                   src=top.from_facility_id, dst=top.to_facility_id, minutes=f"{top.drive_minutes:.0f}")
        return text, [top.order_id], top.order_id

    if any(w in lowered for w in INTENT_WORDS["risk"]):
        from backend.api.public import district_summary
        gaps = next((r["escalate"] for r in district_summary() if r["district_id"] == district_id), {})
        escalate = msg(lang, "agent_escalate", drugs=", ".join(drug_name(d, lang) for d in gaps)) + " " if gaps else ""
        rows = call("list_at_risk", district_id=district_id, exclude_drugs=frozenset(gaps))
        if not rows:
            return escalate + msg(lang, "agent_none_at_risk", district=district), list(gaps), None
        lines = "; ".join(
            msg(lang, "agent_at_risk_line", name=r["name"], facility=r["facility_id"], drug=drug_name(r["drug_id"], lang),
                on_hand=r["on_hand"], demand=f"{r['weekly_demand']:.0f}")
            for r in rows[:5]
        )
        return escalate + msg(lang, "agent_at_risk", district=district, lines=lines), [r["facility_id"] for r in rows[:5]], None

    if any(w in lowered for w in INTENT_WORDS["capacity"]):
        cap = call("get_capacity", district_id=district_id)
        beds, staff = cap["beds"], cap["staff"]
        referral = beds["referrals"][0] if beds["referrals"] else None
        deputation = staff["deputations"][0] if staff["deputations"] else None
        text = msg(lang, "agent_capacity", district=district, full=beds["full_count"], occupied=beds["occupied"], total=beds["total"],
                   present=staff["present"], rostered=staff["rostered"], off_site=len(staff["off_site"]))
        if referral:
            text += " " + msg(lang, "agent_referral", n=referral["patients"], src=referral["from_name"], dst=referral["to_name"])
        if deputation:
            text += " " + msg(lang, "agent_deputation", n=deputation["staff"], role=deputation["role"], src=deputation["from_name"], dst=deputation["to_name"])
        cited = [r["from_id"] for r in beds["referrals"][:1]] + [d["to_id"] for d in staff["deputations"][:1]]
        return text, cited or [district_id], None

    return None


_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")


def _cloud() -> bool:
    from backend.config import get_settings
    return get_settings().mode == "cloud"


def _llm():
    return factory.get("llm")


def _declare(function: str, description: str, **params: str) -> dict:
    return {"name": function, "description": description, "parameters_json_schema": {
        "type": "object", "properties": {k: {"type": "string", "description": v} for k, v in params.items()}, "required": list(params)}}


_DECLARATIONS = [
    _declare("find_facility", "Look up facilities in the officer's district by name; returns IDs.", name="facility name, e.g. Nandgaon"),
    _declare("facility_stock", "Latest reported stock of every medicine at one facility.", facility_id="facility ID, e.g. MH-0000230"),
    _declare("facility_forecast", "Next-week demand forecast and stock-out probability for one medicine at one facility.",
             facility_id="facility ID", medicine="medicine name, e.g. ORS"),
    _declare("at_risk", "Facilities in the district under a week of cover, and medicines short district-wide."),
    _declare("capacity", "Today's beds and staff in the district: full facilities, referrals, staff gaps, off-site check-ins."),
    _declare("orders", "Transfer orders in the district by status, with the most urgent drafts."),
]


def _gemini_tools(question: str, officer: OfficerCtx, lang: str) -> tuple[str, list[str], None] | None:
    """Cloud mode: Gemini answers a question the templates don't cover by calling read-only
    functions. Returns None (the officer gets the help text) locally, on failure, or when the
    answer states a number none of the functions returned."""
    import json
    from backend.i18n import LANG_NAMES, drug_name
    from backend.providers.base import ProviderError
    from backend.runtime import PILOT_DISTRICT, weekly_demand

    if not _cloud():
        return None
    district_id = officer.jurisdiction if "/" in officer.jurisdiction else PILOT_DISTRICT
    seen: list[str] = []   # every tool result, to check the answer's numbers against
    cited: list[str] = []

    def call(name: str, args: dict):
        def tool(tool_name, **kw):
            return tools.call_tool(tool_name, officer.uid, officer.jurisdiction, **kw)
        try:
            if name == "find_facility":
                result = tool("find_facility", query=str(args.get("name", "")), district_id=district_id)
            elif name == "facility_stock":
                fid = str(args.get("facility_id", "")).upper()
                demand = weekly_demand()
                result = [{"medicine": drug_name(r.drug_id, "en"), "on_hand": r.on_hand, "weekly_demand": round(demand.get((fid, r.drug_id), 0.0), 1),
                           "reported": r.reported_at.date().isoformat()} for r in tool("get_stock", facility_id=fid)]
                cited.append(fid)
            elif name == "facility_forecast":
                fid, drug_id = str(args.get("facility_id", "")).upper(), _drug_from(str(args.get("medicine", "")))
                if not drug_id:
                    result = {"error": "unknown medicine"}
                else:
                    f = (tool("get_forecast", facility_id=fid, drug_id=drug_id) or [None])[0]
                    result = {"error": "no forecast"} if f is None else {
                        "medicine": drug_name(drug_id, "en"), "stockout_probability_pct": round(100 * f.stockout_prob),
                        "expected_demand": round(f.p50), "range_low": round(f.p10), "range_high": round(f.p90),
                        "demand_basis": "this facility's own reported use" if f.model == "reported_use" else "last ledger week carried forward"}
                    cited.extend([fid, drug_id])
            elif name == "at_risk":
                from backend.api.public import district_summary
                gaps = next((r["escalate"] for r in district_summary() if r["district_id"] == district_id), {})
                result = {"short_district_wide": [drug_name(d, "en") for d in gaps],
                          "facilities": [{**r, "medicine": drug_name(r.pop("drug_id"), "en")} for r in tool("list_at_risk", district_id=district_id, exclude_drugs=frozenset(gaps))]}
            elif name == "capacity":
                cap = tool("get_capacity", district_id=district_id)
                result = {"date": cap["date"], "generated_baseline_for_unreported": cap["demo_baseline"], "beds": cap["beds"],
                          "staff": {k: v for k, v in cap["staff"].items()}}
            elif name == "orders":
                from collections import Counter
                orders = tool("list_orders", district_id=district_id)
                result = {"by_status": dict(Counter(o.status.value for o in orders)),
                          "drafts": [{"medicine": drug_name(o.drug_id, "en") if o.drug_id else o.kind.value, "units": o.quantity,
                                      "from": o.from_facility_id, "to": o.to_facility_id} for o in orders if o.status.value == "draft"][:5]}
            else:
                result = {"error": f"no function {name}"}
        except PermissionError as e:
            result = {"error": f"outside your jurisdiction: {e}"}
        seen.append(json.dumps(result, default=str))
        return json.loads(seen[-1])

    system = (f"{INSTRUCTIONS}\n\nYou serve a health officer for {district_id}. Answer in {LANG_NAMES.get(lang, 'English')}, "
              "in at most four sentences, using only facts the functions return. Name facilities by name and ID. "
              "If the functions cannot answer, say what you can answer instead.")
    try:
        text = _llm().run_tools(system, question, _DECLARATIONS, call)
    except ProviderError as e:
        _log.warning("agent function calling failed: %s", str(e)[:200])
        return None
    # Grounded means: at least one function answered, and every number in the answer came from a
    # function result (or counts one of its lists). A number only the officer typed is not a fact.
    retrieved = [json.loads(r) for r in seen if '"error"' not in r[:12]]
    known = set(_NUMBER_RE.findall(" ".join(seen).replace(",", ""))) | {str(n) for n in _list_lengths(retrieved)}
    extra = set(_NUMBER_RE.findall(text.replace(",", ""))) - known
    if not text or not retrieved or extra or any(w in text.lower() for w in _ACTION_WORDS if w != "transfer now"):
        _log.warning("agent answer dropped (empty, no function result, new numbers %s, or an action): %s", sorted(extra), text[:200])
        return None
    return text, list(dict.fromkeys(cited)) or [district_id], None
def _list_lengths(value) -> set[int]:
    """How many items each list in a function result holds: "3 facilities" is grounded too."""
    if isinstance(value, list):
        return {len(value)} | {n for v in value for n in _list_lengths(v)}
    if isinstance(value, dict):
        return {n for v in value.values() for n in _list_lengths(v)}
    return set()


_ACTION_WORDS = ("approv", "send", "sent", "transfer now", "order now")


def _with_gemini_note(text: str, question: str, lang: str) -> str:
    """Cloud mode: Gemini adds a one- or two-sentence plain-language reading of the answer the
    tools produced. The tools decide what is true and what happens; the note may not add a
    number the answer lacks or talk about approving or sending, else it is dropped."""
    from backend.config import get_settings
    from backend.i18n import LANG_NAMES
    from backend.providers.base import ProviderError

    if get_settings().mode != "cloud":
        return text
    prompt = (
        f"{INSTRUCTIONS}\n\nA district health officer asked: {question}\n"
        f"The system's answer, from its own stock and forecast data, is:\n{text}\n\n"
        f"In {LANG_NAMES.get(lang, 'English')}, write one or two short sentences saying what this means "
        "for the officer and what to check next. Use only facts from the answer. No new numbers, no "
        "recommendation to approve, send or order anything."
    )
    try:
        note = factory.get("llm").generate(prompt, timeout_s=10).text.strip()  # the officer is waiting
    except ProviderError as e:
        _log.warning("agent note skipped: %s", str(e)[:200])
        return text
    numbers = lambda s: set(_NUMBER_RE.findall(s.replace(",", "")))  # "31,547" is one number
    extra = numbers(note) - numbers(text)
    reason = ("empty" if not note else "too long" if len(note) > 400 else f"new numbers {sorted(extra)}" if extra
              else "mentions an action" if any(w in note.lower() for w in _ACTION_WORDS) else None)
    if reason:
        _log.warning("agent note dropped (%s): %s", reason, note[:200])
        return text
    return f"{text}\n\n{note}"


def ask(question: str, officer: OfficerCtx, lang: str = "en") -> AgentAnswer:
    from backend.i18n import INTENT_WORDS, msg
    log(actor=f"agent:{officer.uid}", action="ask:entry", target_id="agent", payload={"question": question}, jurisdiction=officer.jurisdiction)

    lowered = question.lower()
    if any(w in lowered for w in INTENT_WORDS["action"]):
        text, cited_ids, draft_order_id = msg(lang, "agent_help"), [], None  # refused before any model sees it
    else:
        from_gemini = False
        try:
            answer = _keyword_dispatch(question, officer, lang)
            if answer is None:
                answer = _gemini_tools(question, officer, lang)
                from_gemini = answer is not None
            text, cited_ids, draft_order_id = answer or (msg(lang, "agent_help"), [], None)
        except PermissionError as exc:
            text, cited_ids, draft_order_id = msg(lang, "agent_outside", detail=exc), [], None
        if cited_ids and draft_order_id is None and not from_gemini:
            text = _with_gemini_note(text, question, lang)  # explanations and lists; Gemini answers need no second note

    log(actor=f"agent:{officer.uid}", action="ask:exit", target_id="agent", payload={"answer": text[:200]}, jurisdiction=officer.jurisdiction)
    return AgentAnswer(text=text, cited_ids=cited_ids, draft_order_id=draft_order_id)
