"""Officer routes: view, propose, approve/reject orders; facility detail;
manual escalation sweep (modular-plan.md §2.3, step 33). Approval is the
one human gate every transfer/deputation/referral must pass through --
FR6/FR7 ("no order executes without officer approval") is enforced here.

Jurisdiction is always derived from the order's own facilities via the
facility directory, never from a caller-supplied district.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from backend.deps import AuthUser, check_jurisdiction, require_role
from backend.domain import AuditEvent, OrderKind, OrderStatus, TransferOrder
from backend.providers import factory
from backend.runtime import ORDER_LOCK

from backend.action.alerts import send_transfer_alerts
from backend.action.escalate import sweep
from backend.action.sign_order import sign

router = APIRouter(prefix="/officer", tags=["officer"])
log = logging.getLogger(__name__)
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
    """Orders with what an officer needs to approve safely: facility names, stock at both ends
    after earlier approvals, days of cover before and after (the destination counting every
    draft to it, the source after this one), how old the reports are, and whether the drug is
    short district-wide. Most urgent first; expired drafts are left out."""
    check_jurisdiction(user, district_id)
    from ml.data.facilities import served_facility_index as facility_index
    from backend.api.public import district_summary
    from backend.runtime import latest_records, projected_stock, weekly_demand
    index, latest = facility_index(), latest_records()
    try:
        demand = weekly_demand()
    except FileNotFoundError:
        demand = {}
    gaps = {r["district_id"]: r["escalate"] for r in district_summary()}
    from backend.runtime import in_scope

    # Expired drafts (superseded solver runs) are most of the store and grow with every proposal; skip them.
    live = factory.get("store_live")
    orders = [o for status in OrderStatus if status != OrderStatus.EXPIRED for o in live.query("orders", {"status": status})]
    orders = [o for o in orders if any(in_scope(d, district_id) for d in _order_districts(o))]
    stock = projected_stock({fid for o in orders for fid in (o.from_facility_id, o.to_facility_id)})
    incoming: dict[tuple, int] = {}
    for o in orders:
        if o.status == OrderStatus.DRAFT and o.quantity:
            incoming[(o.to_facility_id, o.drug_id)] = incoming.get((o.to_facility_id, o.drug_id), 0) + o.quantity
    now = datetime.now(timezone.utc)

    def cover(key, units):
        need = demand.get(key, 0.0)
        return round(7 * units / need, 1) if need >= 1.0 and units is not None else None

    def enrich(o: TransferOrder) -> dict:
        dst, src = (o.to_facility_id, o.drug_id), (o.from_facility_id, o.drug_id)
        dst_units = stock.get(dst) if dst in stock else None
        src_units = stock.get(src) if src in stock else None
        draft = o.status == OrderStatus.DRAFT
        report = latest.get(dst)
        name = lambda fid: index[fid].name if fid in index else None
        return {**o.model_dump(mode="json"), "from_name": name(o.from_facility_id), "to_name": name(o.to_facility_id),
                "dest_on_hand": dst_units, "dest_cover_days": cover(dst, dst_units),
                "dest_cover_after_days": cover(dst, None if dst_units is None else dst_units + (incoming.get(dst, 0) if draft else 0)),
                "src_on_hand_after": None if src_units is None else src_units - (o.quantity or 0) * draft,
                "src_cover_after_days": cover(src, None if src_units is None else src_units - (o.quantity or 0) * draft),
                "report_age_days": None if report is None else (now - report.reported_at).days,
                "district_gap": o.drug_id in gaps.get(index[o.to_facility_id].district_id if o.to_facility_id in index else "", {})}

    rows = [enrich(o) for o in orders]
    return sorted(rows, key=lambda r: (r["dest_cover_days"] is None, r["dest_cover_days"] or 0.0))


@router.post("/orders/{order_id}/approve")
def approve_order(order_id: str, user: AuthUser = Depends(OFFICER)):
    """Signs a draft, after checking the source still holds the units once earlier approvals
    are counted, then sends both facilities the signed order. If the alerts fail the order
    stays approved without `alerted_at`, and approving again resends them."""
    order = _authorised_order(order_id, user)
    if order.status == OrderStatus.APPROVED and order.alerted_at is not None:
        return order  # idempotent: no double-signing, no duplicate alerts
    if order.status not in (OrderStatus.DRAFT, OrderStatus.APPROVED):
        raise HTTPException(409, f"cannot approve an order that is {order.status.value}")

    live = factory.get("store_live")
    if order.status == OrderStatus.DRAFT:
        signed = sign(order, approved_by=f"officer:{user.uid}")
        with ORDER_LOCK:  # a proposal may have expired it, or a second click approved it, while it was signed
            current = live.get("orders", order_id)
            if current.status == OrderStatus.APPROVED:
                return current
            if current.status != OrderStatus.DRAFT:
                raise HTTPException(409, f"cannot approve an order that is {current.status.value}")
            if current.kind == OrderKind.DRUG_TRANSFER:
                from backend.runtime import projected_stock
                available = projected_stock({current.from_facility_id}).get((current.from_facility_id, current.drug_id), 0.0)
                if current.quantity > available:
                    raise HTTPException(409, f"the source now has {available:g} units after earlier approvals and reports, "
                                             f"fewer than the {current.quantity} ordered: propose transfers again")
            live.put("orders", order_id, signed)
        _audit(user, "approve_order", signed)
    else:
        signed = order

    from ml.data.facilities import served_facility_index as facility_index
    from backend.runtime import phone_for_facility
    index = facility_index()
    try:
        # shortcut: a failure resends both facilities' alerts on retry, so one may get a duplicate;
        # per-recipient delivery tracking needs Twilio status callbacks.
        send_transfer_alerts(
            signed, index[signed.from_facility_id], index[signed.to_facility_id],
            phone_for_facility(signed.from_facility_id), phone_for_facility(signed.to_facility_id),
        )
    except Exception as e:  # noqa: BLE001 -- any provider failure: the approval stands, the alert is retried
        log.warning("alerts for %s failed: %s", order_id, e)
        raise HTTPException(502, "Approved and signed, but the WhatsApp alerts did not go out. Approve again to resend them.")
    with ORDER_LOCK:
        alerted = live.get("orders", order_id).model_copy(update={"alerted_at": datetime.now(timezone.utc)})
        live.put("orders", order_id, alerted)
    return alerted


@router.post("/orders/{order_id}/received")
def receive_order(order_id: str, user: AuthUser = Depends(OFFICER)):
    """Records that the destination got the goods (the nurse can also reply RECEIVED <code>)."""
    order = _authorised_order(order_id, user)
    received = mark_received(order)
    _audit(user, "receive_order", received)
    return received


def mark_received(order: TransferOrder) -> TransferOrder:
    if order.status == OrderStatus.RECEIVED:
        return order
    if order.status not in (OrderStatus.APPROVED, OrderStatus.DISPATCHED):
        raise HTTPException(409, f"cannot receive an order that is {order.status.value}")
    live = factory.get("store_live")
    with ORDER_LOCK:
        received = live.get("orders", order.order_id).model_copy(
            update={"status": OrderStatus.RECEIVED, "received_at": datetime.now(timezone.utc)})
        live.put("orders", order.order_id, received)
    return received


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


@router.get("/capacity/{district_id:path}")
def capacity(district_id: str, user: AuthUser = Depends(OFFICER)):
    """Today's beds and staff: full facilities with referral suggestions, staff gaps with deputation suggestions."""
    check_jurisdiction(user, district_id)
    from backend.capacity import district_capacity
    return district_capacity(district_id)


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
