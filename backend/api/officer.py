"""Officer routes: view, propose, approve/reject orders; facility detail;
manual escalation sweep (modular-plan.md §2.3, step 33). Approval is the
one human gate every transfer/deputation/referral must pass through --
FR6/FR7 ("no order executes without officer approval") is enforced here.

Jurisdiction is always derived from the order's own facilities via the
facility directory, never from a caller-supplied district.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from backend.deps import AuthUser, check_jurisdiction, require_role
from backend.domain import AuditEvent, OrderStatus, TransferOrder
from backend.providers import factory
from backend.runtime import ORDER_LOCK

from backend.action.alerts import send_transfer_alerts
from backend.action.escalate import sweep
from backend.action.sign_order import sign

router = APIRouter(prefix="/officer", tags=["officer"])
OFFICER = require_role("block", "district", "state")


def _order_districts(order: TransferOrder) -> set[str]:
    from ml.data.facilities import served_facility_index as facility_index
    index = facility_index()
    districts = set()
    for fid in (order.from_facility_id, order.to_facility_id):
        facility = index.get(fid)
        if facility is None:
            raise HTTPException(403, f"order references unknown facility {fid}")
        districts.add(facility.district_id)
    return districts


def _authorised_order(order_id: str, user: AuthUser) -> TransferOrder:
    order = factory.get("store_live").get("orders", order_id)
    if order is None:
        raise HTTPException(404, "order not found")
    for district in _order_districts(order):
        check_jurisdiction(user, district)
    return order


def _audit(user: AuthUser, action: str, order: TransferOrder) -> None:
    district = sorted(_order_districts(order))[0]
    factory.get("store_live").put("audit_events", str(uuid.uuid4()), AuditEvent(
        event_id=str(uuid.uuid4()), at=datetime.now(timezone.utc), actor=f"officer:{user.uid}",
        action=action, target_id=order.order_id, payload_json=json.dumps({"districts": sorted(_order_districts(order))}),
        jurisdiction=district,
    ))


@router.get("/orders/{district_id:path}")
def list_orders(district_id: str, user: AuthUser = Depends(OFFICER)):
    """Orders with what an officer triages by: facility names, the destination's days of
    cover for that drug, and whether the drug is short district-wide (a transfer then only
    spreads stock; procurement is the fix). Most urgent first; expired drafts are left out."""
    check_jurisdiction(user, district_id)
    from ml.data.facilities import served_facility_index as facility_index
    from backend.api.public import district_summary
    from backend.runtime import latest_records, weekly_demand
    index, latest = facility_index(), latest_records()
    try:
        demand = weekly_demand()
    except FileNotFoundError:
        demand = {}
    gaps = next((r["escalate"] for r in district_summary() if r["district_id"] == district_id), {})

    def enrich(o: TransferOrder) -> dict:
        key = (o.to_facility_id, o.drug_id)
        need = demand.get(key, 0.0)
        record = latest.get(key)
        cover = round(7 * record.on_hand / need, 1) if record is not None and need >= 1.0 else None
        name = lambda fid: index[fid].name if fid in index else None
        return {**o.model_dump(mode="json"), "from_name": name(o.from_facility_id), "to_name": name(o.to_facility_id),
                "dest_cover_days": cover, "district_gap": o.drug_id in gaps}

    # Expired drafts (superseded solver runs) are most of the store and grow with every proposal; skip them.
    live = factory.get("store_live")
    orders = [o for status in OrderStatus if status != OrderStatus.EXPIRED for o in live.query("orders", {"status": status})]
    rows = [enrich(o) for o in orders if district_id in _order_districts(o)]
    return sorted(rows, key=lambda r: (r["dest_cover_days"] is None, r["dest_cover_days"] or 0.0))


@router.post("/orders/{order_id}/approve")
def approve_order(order_id: str, user: AuthUser = Depends(OFFICER)):
    order = _authorised_order(order_id, user)
    if order.status == OrderStatus.APPROVED:
        return order  # idempotent: no double-signing, no duplicate alerts
    if order.status != OrderStatus.DRAFT:
        raise HTTPException(409, f"cannot approve an order that is {order.status.value}")

    signed = sign(order, approved_by=f"officer:{user.uid}")
    live = factory.get("store_live")
    with ORDER_LOCK:  # a proposal may have expired it, or a second click approved it, while it was signed
        current = live.get("orders", order_id)
        if current.status == OrderStatus.APPROVED:
            return current
        if current.status != OrderStatus.DRAFT:
            raise HTTPException(409, f"cannot approve an order that is {current.status.value}")
        live.put("orders", order_id, signed)
    _audit(user, "approve_order", signed)

    from ml.data.facilities import served_facility_index as facility_index
    from backend.runtime import phone_for_facility
    index = facility_index()
    send_transfer_alerts(
        signed, index[signed.from_facility_id], index[signed.to_facility_id],
        phone_for_facility(signed.from_facility_id), phone_for_facility(signed.to_facility_id),
    )
    return signed


@router.post("/orders/{order_id}/reject")
def reject_order(order_id: str, user: AuthUser = Depends(OFFICER)):
    order = _authorised_order(order_id, user)
    if order.status == OrderStatus.REJECTED:
        return order
    if order.status != OrderStatus.DRAFT:
        raise HTTPException(409, f"cannot reject an order that is {order.status.value}")
    live = factory.get("store_live")
    with ORDER_LOCK:
        current = live.get("orders", order_id)
        if current.status != OrderStatus.DRAFT:
            raise HTTPException(409, f"cannot reject an order that is {current.status.value}")
        rejected = current.model_copy(update={"status": OrderStatus.REJECTED})
        live.put("orders", order_id, rejected)
    _audit(user, "reject_order", rejected)
    return rejected


@router.post("/propose/{district_id:path}")
def propose_orders(district_id: str, user: AuthUser = Depends(OFFICER)):
    """Runs the forecast-driven transfer solver for one district and saves
    the proposals as drafts. Drafts only: approval is a separate call."""
    check_jurisdiction(user, district_id)
    from backend.runtime import propose_for_district, replace_drafts
    return replace_drafts(district_id, propose_for_district(district_id))


@router.post("/escalation/sweep")
def run_escalation(user: AuthUser = Depends(require_role("state"))):
    return sweep()


@router.get("/districts/{district_id:path}/facilities")
def district_facilities(district_id: str, user: AuthUser = Depends(OFFICER)):
    check_jurisdiction(user, district_id)
    from ml.data.facilities import served_facility_index as facility_index
    from backend.runtime import below_cover, latest_records
    short: dict[str, list[str]] = {}
    for r in latest_records().values():
        if below_cover(r):
            short.setdefault(r.facility_id, []).append(r.drug_id)
    return [
        {"facility_id": f.facility_id, "name": f.name, "block": f.block, "type": f.facility_type.value,
         "lat": f.lat, "lon": f.lon, "at_risk": f.facility_id in short, "short_count": len(short.get(f.facility_id, [])),
         "short_drugs": sorted(short.get(f.facility_id, []))}
        for f in facility_index().values() if f.district_id == district_id
    ]


@router.get("/facility/{facility_id}")
def facility_detail(facility_id: str, user: AuthUser = Depends(OFFICER)):
    from ml.data.facilities import served_facility_index as facility_index
    from backend.runtime import forecast_panel, latest_stock
    from ml.forecast.service import latest_forecasts
    facility = facility_index().get(facility_id)
    if facility is None:
        raise HTTPException(404, "facility not found")
    check_jurisdiction(user, facility.district_id)
    stock = factory.get("store_live").query("stock_records", {"facility_id": facility_id})
    drug_ids = sorted({r.drug_id for r in stock})
    return {
        "facility": facility,
        "stock": sorted(stock, key=lambda r: r.drug_id),
        "forecasts": latest_forecasts([facility_id], drug_ids, panel=forecast_panel(), on_hand=latest_stock({facility_id})) if drug_ids else [],
    }
