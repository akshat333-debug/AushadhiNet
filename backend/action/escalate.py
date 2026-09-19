"""Time-boxed escalation ladder: facility -> block -> district -> state
(modular-plan.md §5.5). A draft order that sits unactioned past
`escalation_hours` bumps one level and re-alerts; in cloud mode this is
what Cloud Scheduler drives periodically, calling `sweep()` on a timer --
the decision logic itself has no dependency on the scheduler.
"""
from __future__ import annotations

from datetime import datetime, timezone

from backend.config import get_settings
from backend.domain import OrderStatus, TransferOrder
from backend.providers import factory

LADDER = ("facility", "block", "district", "state")


def next_escalation_level(order: TransferOrder, now: datetime, escalation_hours: int) -> int:
    """How many ladder steps this order should currently be at, based on
    elapsed time since creation. Capped at the top of the ladder."""
    if order.status != OrderStatus.DRAFT:
        return order.escalation_level  # only unactioned orders escalate
    elapsed_hours = (now - order.created_at).total_seconds() / 3600.0
    steps_due = int(elapsed_hours // escalation_hours)
    return min(steps_due, len(LADDER) - 1)


def sweep(now: datetime | None = None) -> list[TransferOrder]:
    """Checks every draft order in the live store and escalates any that
    are overdue, sending a re-alert at the new level. Returns the orders
    that were escalated this sweep."""
    settings = get_settings()
    now = now or datetime.now(timezone.utc)
    live = factory.get("store_live")
    messaging = factory.get("messaging")

    escalated = []
    for order in live.query("orders", {}):
        if order.status != OrderStatus.DRAFT:
            continue
        new_level = next_escalation_level(order, now, settings.escalation_hours)
        if new_level > order.escalation_level:
            updated = order.model_copy(update={"escalation_level": new_level})
            live.put("orders", order.order_id, updated)
            messaging.send_text(
                f"escalation:{LADDER[new_level]}",
                f"Order {order.order_id[:8]} unactioned for {new_level * settings.escalation_hours}h+, "
                f"now escalated to {LADDER[new_level]} level.",
            )
            escalated.append(updated)
    return escalated
