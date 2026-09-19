"""Renders a transfer order as a human-readable, batch-level manifest
(modular-plan.md §5.5) -- what actually gets sent as the WhatsApp/voice
alert body and shown on the dashboard.
"""
from __future__ import annotations

from backend.domain import Facility, TransferOrder


def render(order: TransferOrder, from_facility: Facility, to_facility: Facility, drug_name: str | None = None) -> str:
    lines = [
        f"Transfer Order {order.order_id[:8]} [{order.status.value.upper()}]",
        f"From: {from_facility.name} ({from_facility.facility_id})",
        f"To: {to_facility.name} ({to_facility.facility_id})",
        f"Drive time: {order.drive_minutes:.0f} min",
    ]
    if drug_name and order.quantity is not None:
        lines.append(f"Drug: {drug_name} x{order.quantity}")
    if order.batches:
        lines.append("Batches:")
        for b in order.batches:
            expiry = b.expiry.date().isoformat() if b.expiry else "n/a"
            lines.append(f"  - {b.batch_no}: {b.quantity} units, expiry {expiry}")
    if order.staff_id_hash:
        lines.append(f"Staff deputation: {order.staff_id_hash}")
    if order.patient_count:
        lines.append(f"Patients referred: {order.patient_count}")
    lines.append(f"Rationale: {order.rationale}")
    if order.signature:
        lines.append(f"Signature: {order.signature[:16]}...")
    return "\n".join(lines)
