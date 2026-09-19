"""The officer agent's tool registry (modular-plan.md §2.6). This is
where AC7's guarantee actually lives: TOOL_REGISTRY contains no write/
send/approve/execute capability at all. A prompt injection cannot make
the agent call a tool that does not exist -- this is enforced structurally
here, not by asking the model nicely not to.

`propose_order` is the one tool that creates anything, and it can only
ever create a `status="draft"` order (ml.optimize.service.propose already
guarantees this; this wrapper additionally refuses any caller-supplied
status override outright, so even a malicious/buggy caller cannot smuggle
one in).
"""
from __future__ import annotations

from backend.domain import Facility, TransferOrder
from backend.providers import factory

from backend.agent.audit import log_tool_call
from ml.data.facilities import load_facilities
from ml.forecast.service import latest_forecasts
from ml.optimize.service import propose as _optimize_propose

# Forbidden by construction: no tool named anything like these may ever
# be added to TOOL_REGISTRY. Checked by tests/backend/agent/test_tools.py
# via name inspection, not by trusting this comment.
_FORBIDDEN_NAME_FRAGMENTS = ("approve", "send", "write", "execute", "dispatch", "sign", "reject")


def get_facility(facility_id: str) -> Facility | None:
    live = factory.get("store_live")
    cached = live.get("facilities", facility_id)
    if cached is not None:
        return cached
    matches = [f for f in load_facilities() if f.facility_id == facility_id]
    return matches[0] if matches else None


def get_stock(facility_id: str, drug_id: str | None = None) -> list:
    live = factory.get("store_live")
    filters = {"facility_id": facility_id}
    if drug_id:
        filters["drug_id"] = drug_id
    return live.query("stock_records", filters)


def get_forecast(facility_id: str, drug_id: str) -> list:
    return latest_forecasts([facility_id], [drug_id])


def list_orders(district_id: str) -> list:
    live = factory.get("store_live")
    return [o for o in live.query("orders", {}) if getattr(o, "district_id", None) in (None, district_id)]


def explain_risk(facility_id: str, drug_id: str) -> str:
    forecasts = get_forecast(facility_id, drug_id)
    if not forecasts:
        return f"No forecast available yet for {drug_id} at {facility_id}."
    f = forecasts[0]
    return (
        f"{facility_id}'s {drug_id} stock-out probability over the next {f.horizon} weeks is "
        f"{f.stockout_prob:.0%}, with expected demand around {f.p50:.0f} units (range {f.p10:.0f}-{f.p90:.0f})."
    )


def propose_order(facilities: list[Facility], drug_ids: list[str], cold_chain_by_drug: dict, stock_by_facility_drug: dict, **kwargs) -> list[TransferOrder]:
    if "status" in kwargs or "approved" in kwargs:
        raise ValueError("propose_order does not accept a status override -- every proposal is a draft, always")
    orders = _optimize_propose(facilities, drug_ids, cold_chain_by_drug, stock_by_facility_drug)
    for order in orders:
        assert order.status.value == "draft"
    return orders


TOOL_REGISTRY = {
    "get_facility": get_facility,
    "get_stock": get_stock,
    "get_forecast": get_forecast,
    "list_orders": list_orders,
    "explain_risk": explain_risk,
    "propose_order": propose_order,
}


def call_tool(name: str, officer_uid: str, jurisdiction: str, **kwargs):
    if name not in TOOL_REGISTRY:
        raise KeyError(f"unknown tool '{name}'")
    result = TOOL_REGISTRY[name](**kwargs)
    log_tool_call(name, officer_uid, jurisdiction, kwargs, result_summary=str(result)[:200])
    return result
