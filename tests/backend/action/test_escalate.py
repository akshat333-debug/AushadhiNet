"""DoD test for backend/action/escalate.py (step 34)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.domain import BatchLine, OrderKind, OrderStatus, TransferOrder
from backend.providers import factory

from backend.action.escalate import next_escalation_level, sweep


def _order(created_at, escalation_level=0, status=OrderStatus.DRAFT):
    return TransferOrder(
        order_id="o1", kind=OrderKind.DRUG_TRANSFER, from_facility_id="F1", to_facility_id="F2",
        drug_id="ors", quantity=10, batches=[BatchLine(batch_no="B1", quantity=10)],
        drive_minutes=25.0, rationale="test", created_at=created_at, created_by="solver",
        status=status, escalation_level=escalation_level,
    )


def test_no_escalation_within_first_window():
    now = datetime.now(timezone.utc)
    order = _order(created_at=now - timedelta(hours=1))
    assert next_escalation_level(order, now, escalation_hours=24) == 0


def test_escalates_one_level_after_one_window():
    now = datetime.now(timezone.utc)
    order = _order(created_at=now - timedelta(hours=25))
    assert next_escalation_level(order, now, escalation_hours=24) == 1


def test_caps_at_top_of_ladder():
    now = datetime.now(timezone.utc)
    order = _order(created_at=now - timedelta(hours=1000))
    assert next_escalation_level(order, now, escalation_hours=24) == 3  # state, index 3


def test_approved_order_never_escalates():
    now = datetime.now(timezone.utc)
    order = _order(created_at=now - timedelta(hours=1000), status=OrderStatus.APPROVED)
    assert next_escalation_level(order, now, escalation_hours=24) == 0


def test_sweep_escalates_overdue_orders_and_alerts():
    now = datetime.now(timezone.utc)
    live = factory.get("store_live")
    overdue = _order(created_at=now - timedelta(hours=48))
    fresh = _order(created_at=now - timedelta(hours=1))
    fresh = fresh.model_copy(update={"order_id": "o2"})
    live.put("orders", overdue.order_id, overdue)
    live.put("orders", fresh.order_id, fresh)

    escalated = sweep(now=now)
    assert len(escalated) == 1
    assert escalated[0].order_id == "o1"
    assert escalated[0].escalation_level >= 1

    messaging = factory.get("messaging")
    assert any(m.to.startswith("escalation:") for m in messaging.sent)
