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
    from backend.runtime import forecast_panel, latest_stock
    return latest_forecasts([facility_id], [drug_id], panel=forecast_panel(), on_hand=latest_stock({facility_id}))


def list_orders(district_id: str) -> list:
    from ml.data.facilities import served_facility_index as facility_index
    index = facility_index()
    return [
        o for o in factory.get("store_live").query("orders", {})
        if district_id in {getattr(index.get(o.from_facility_id), "district_id", None), getattr(index.get(o.to_facility_id), "district_id", None)}
    ]


def list_at_risk(district_id: str, limit: int = 10) -> list[dict]:
    """Facility x drug pairs under one week of cover in a district, lowest stock first."""
    from backend.runtime import below_cover, latest_records, weekly_demand
    from ml.data.facilities import served_facility_index as facility_index
    index = facility_index()
    demand = weekly_demand()
    rows = [
        {"facility_id": r.facility_id, "name": index[r.facility_id].name, "drug_id": r.drug_id,
         "on_hand": r.on_hand, "weekly_demand": round(demand.get((r.facility_id, r.drug_id), 0.0), 1)}
        for r in latest_records().values()
        if r.facility_id in index and index[r.facility_id].district_id == district_id and below_cover(r)
    ]
    return sorted(rows, key=lambda x: x["on_hand"] - x["weekly_demand"])[:limit]


def explain_risk(facility_id: str, drug_id: str) -> str:
    forecasts = get_forecast(facility_id, drug_id)
    if not forecasts:
        return f"No forecast available yet for {drug_id} at {facility_id}."
    f = forecasts[0]
    return (
        f"{facility_id}'s {drug_id} stock-out probability over the next {f.horizon} week(s) is "
        f"{f.stockout_prob:.0%}, with expected demand around {f.p50:.0f} units (range {f.p10:.0f}-{f.p90:.0f})."
    )


def propose_order(facilities: list[Facility], drug_ids: list[str], cold_chain_by_drug: dict, stock_by_facility_drug: dict, **kwargs) -> list[TransferOrder]:
    if "status" in kwargs or "approved" in kwargs:
        raise ValueError("propose_order does not accept a status override -- every proposal is a draft, always")
    orders = _optimize_propose(facilities, drug_ids, cold_chain_by_drug, stock_by_facility_drug)
    for order in orders:
        assert order.status.value == "draft"
    return orders


def propose_transfers(district_id: str) -> list[TransferOrder]:
    """Runs the solver for a district and stores the proposals as drafts
    for an officer to approve or reject. Cannot produce anything but drafts."""
    from backend.runtime import propose_for_district, replace_drafts
    return replace_drafts(district_id, propose_for_district(district_id))


TOOL_REGISTRY = {
    "get_facility": get_facility,
    "get_stock": get_stock,
    "get_forecast": get_forecast,
    "list_orders": list_orders,
    "explain_risk": explain_risk,
    "propose_order": propose_order,
    "list_at_risk": list_at_risk,
    "propose_transfers": propose_transfers,
}


def _check_scope(jurisdiction: str, kwargs: dict) -> None:
    """Tools act for one officer: every facility/district argument must be inside their jurisdiction."""
    from fastapi import HTTPException
    from backend.deps import AuthUser, check_jurisdiction
    from ml.data.facilities import served_facility_index as facility_index
    user = AuthUser(uid="agent", role="district", jurisdiction=jurisdiction)
    districts = []
    if "facility_id" in kwargs:
        facility = facility_index().get(kwargs["facility_id"])
        if facility is None:
            raise PermissionError(f"unknown facility {kwargs['facility_id']}")
        districts.append(facility.district_id)
    if "district_id" in kwargs:
        districts.append(kwargs["district_id"])
    for district in districts:
        try:
            check_jurisdiction(user, district)
        except HTTPException as exc:
            raise PermissionError(exc.detail) from exc


def call_tool(name: str, officer_uid: str, jurisdiction: str, **kwargs):
    if name not in TOOL_REGISTRY:
        raise KeyError(f"unknown tool '{name}'")
    _check_scope(jurisdiction, kwargs)
    result = TOOL_REGISTRY[name](**kwargs)
    log_tool_call(name, officer_uid, jurisdiction, kwargs, result_summary=str(result)[:200])
    return result
