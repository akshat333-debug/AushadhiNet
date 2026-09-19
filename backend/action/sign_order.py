"""Signs an approved transfer order (modular-plan.md §5.5): a tamper-
evident manifest, not just a status flag. The canonical payload excludes
the signature and approval metadata themselves (avoiding circularity) but
covers everything that would matter if tampered with: who, what, how much,
which batches.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from backend.domain import OrderStatus, TransferOrder
from backend.providers import factory
from backend.providers.base import ProviderError


def _canonical_payload(order: TransferOrder) -> bytes:
    payload = {
        "order_id": order.order_id, "kind": order.kind.value,
        "from_facility_id": order.from_facility_id, "to_facility_id": order.to_facility_id,
        "drug_id": order.drug_id, "quantity": order.quantity,
        "batches": [b.model_dump(mode="json") for b in order.batches],
        "staff_id_hash": order.staff_id_hash, "patient_count": order.patient_count,
        "created_at": order.created_at.isoformat(),
    }
    return json.dumps(payload, sort_keys=True).encode("utf-8")


def sign(order: TransferOrder, approved_by: str) -> TransferOrder:
    """Approves and signs in one step: an order is only ever signed at the
    moment it is approved (the domain model forbids a signature on a
    draft), so there is no separate "approve, then later sign" gap for a
    signature to be forged into."""
    if order.status == OrderStatus.DRAFT:
        order = order.model_copy(update={
            "status": OrderStatus.APPROVED, "approved_by": approved_by,
            "approved_at": datetime.now(timezone.utc),
        })
    signer = factory.get("sign")
    signature = signer.sign(_canonical_payload(order))
    return order.model_copy(update={"signature": signature})


def verify(order: TransferOrder) -> bool:
    if order.signature is None:
        return False
    signer = factory.get("sign")
    try:
        return signer.verify(_canonical_payload(order), order.signature)
    except ProviderError:
        return False
