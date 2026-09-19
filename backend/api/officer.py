"""Officer routes: view orders, approve/reject (modular-plan.md §2.3,
step 33). Approval is the one human gate every transfer/deputation/
referral must pass through -- FR6/FR7 ("no order executes without officer
approval") is enforced here, not just documented.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.deps import AuthUser, check_jurisdiction, require_role
from backend.domain import OrderStatus
from backend.providers import factory

from backend.action.sign_order import sign

router = APIRouter(prefix="/officer", tags=["officer"])


@router.get("/orders/{district_id:path}")
def list_orders(district_id: str, user: AuthUser = Depends(require_role("block", "district", "state"))):
    check_jurisdiction(user, district_id)
    live = factory.get("store_live")
    return live.query("orders", {})


@router.post("/orders/{order_id}/approve")
def approve_order(order_id: str, district_id: str, user: AuthUser = Depends(require_role("block", "district", "state"))):
    check_jurisdiction(user, district_id)
    live = factory.get("store_live")
    order = live.get("orders", order_id)
    if order is None:
        raise HTTPException(404, "order not found")

    if order.status != OrderStatus.DRAFT:
        # idempotent: approving an already-approved order just returns it,
        # rather than erroring or double-signing
        return order

    signed = sign(order, approved_by=f"officer:{user.uid}")
    live.put("orders", order_id, signed)

    from backend.domain import AuditEvent
    import json
    import uuid
    from datetime import datetime, timezone
    live.put("audit_events", str(uuid.uuid4()), AuditEvent(
        event_id=str(uuid.uuid4()), at=datetime.now(timezone.utc), actor=f"officer:{user.uid}",
        action="approve_order", target_id=order_id, payload_json=json.dumps({"district_id": district_id}),
        jurisdiction=district_id,
    ))
    return signed


@router.post("/orders/{order_id}/reject")
def reject_order(order_id: str, district_id: str, user: AuthUser = Depends(require_role("block", "district", "state"))):
    check_jurisdiction(user, district_id)
    live = factory.get("store_live")
    order = live.get("orders", order_id)
    if order is None:
        raise HTTPException(404, "order not found")

    rejected = order.model_copy(update={"status": OrderStatus.REJECTED})
    live.put("orders", order_id, rejected)
    return rejected
