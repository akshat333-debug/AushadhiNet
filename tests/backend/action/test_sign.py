"""DoD test for backend/action/sign_order.py + render_order.py (step 32)."""
from __future__ import annotations

from datetime import datetime, timezone

from backend.domain import BatchLine, Facility, FacilityType, OrderKind, OrderStatus, TransferOrder

from backend.action.render_order import render
from backend.action.sign_order import sign, verify


def _order(**overrides):
    base = dict(
        order_id="o1", kind=OrderKind.DRUG_TRANSFER, from_facility_id="F1", to_facility_id="F2",
        drug_id="ors", quantity=10, batches=[BatchLine(batch_no="B1", quantity=10)],
        drive_minutes=25.0, rationale="stock-out risk", created_at=datetime.now(timezone.utc),
        created_by="solver",
    )
    base.update(overrides)
    return TransferOrder(**base)


def test_sign_approves_a_draft_and_produces_a_verifiable_signature():
    order = _order()
    signed = sign(order, approved_by="officer:u1")
    assert signed.status == OrderStatus.APPROVED
    assert signed.approved_by == "officer:u1"
    assert signed.signature is not None
    assert verify(signed) is True


def test_tampering_with_quantity_after_signing_fails_verification():
    order = _order()
    signed = sign(order, approved_by="officer:u1")
    tampered = signed.model_copy(update={"quantity": 999})
    assert verify(tampered) is False


def test_unsigned_order_fails_verification():
    order = _order()
    assert verify(order) is False


def test_signing_is_idempotent_content_wise():
    """Signing the same order twice (e.g. a retried request) produces a
    signature that still verifies -- it doesn't corrupt state."""
    order = _order()
    signed_once = sign(order, approved_by="officer:u1")
    signed_again = sign(signed_once, approved_by="officer:u1")
    assert verify(signed_again) is True


def test_render_includes_facilities_drug_and_batches():
    order = sign(_order(), approved_by="officer:u1")
    f1 = Facility(facility_id="F1", name="PHC Alpha", state_code="MH", district_id="mh/nashik", facility_type=FacilityType.PHC, lat=20.0, lon=73.8)
    f2 = Facility(facility_id="F2", name="PHC Beta", state_code="MH", district_id="mh/nashik", facility_type=FacilityType.PHC, lat=20.1, lon=73.9)
    text = render(order, f1, f2, drug_name="ORS")
    assert "PHC Alpha" in text and "PHC Beta" in text
    assert "ORS" in text and "B1" in text
    assert "APPROVED" in text
