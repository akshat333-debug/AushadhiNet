"""The officer's order list: most urgent destination first, district-wide gaps flagged, expired
drafts left out. "Approve the most urgent" signs whatever this puts on top."""
from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.domain import BatchLine, Confidence, ConfidenceSource, OrderKind, OrderStatus, RecordStatus, StockRecord, TransferOrder
from backend.providers import factory

OFFICER = {"Authorization": "Bearer dev:o1:district:mh/nashik"}


def _stock(facility_id, drug_id, on_hand):
    live = factory.get("store_live")
    live.put("stock_records", f"s-{facility_id}-{drug_id}", StockRecord(
        record_id=f"s-{facility_id}-{drug_id}", facility_id=facility_id, drug_id=drug_id,
        reported_at=datetime.now(timezone.utc), as_of_date=date.today(), on_hand=on_hand, status=RecordStatus.CONFIRMED,
        confidence=Confidence(field_confidence={"on_hand": 1.0}, overall=1.0, source=ConfidenceSource.MANUAL),
        reporter_phone_hash="h", raw_message_id="m",
    ))


def _order(order_id, src, dst, drug_id, status=OrderStatus.DRAFT):
    factory.get("store_live").put("orders", order_id, TransferOrder(
        order_id=order_id, kind=OrderKind.DRUG_TRANSFER, from_facility_id=src, to_facility_id=dst, drug_id=drug_id,
        quantity=5, batches=[BatchLine(batch_no="B1", quantity=5)], drive_minutes=20.0, rationale="test",
        status=status, created_at=datetime.now(timezone.utc), created_by="solver",
    ))


def test_orders_are_most_urgent_first_with_gaps_flagged_and_expired_left_out(monkeypatch):
    import backend.runtime as runtime
    from ml.data.facilities import load_facilities
    a, b, c = (f.facility_id for f in load_facilities(state="Maharashtra", district="Nashik")[:3])
    monkeypatch.setattr(runtime, "weekly_demand", lambda: {(b, "ors"): 70.0, (c, "ors"): 70.0, (b, "zinc-20mg"): 70.0})
    _stock(a, "ors", 1000)    # the district has ORS to spare: not a district-wide gap
    _stock(b, "ors", 7)       # 0.7 days of cover
    _stock(c, "ors", 70)      # 7 days
    _stock(b, "zinc-20mg", 0)  # zinc is short everywhere: a district-wide gap
    _order("o-c-ors", a, c, "ors")
    _order("o-b-ors", a, b, "ors")
    _order("o-b-zinc", a, b, "zinc-20mg")
    _order("o-old", a, b, "ors", OrderStatus.EXPIRED)

    rows = TestClient(create_app()).get("/officer/orders/mh/nashik", headers=OFFICER).json()
    assert [r["order_id"] for r in rows] == ["o-b-zinc", "o-b-ors", "o-c-ors"]
    assert [r["dest_cover_days"] for r in rows] == [0.0, 0.7, 7.0]
    assert [r["district_gap"] for r in rows] == [True, False, False]
    # The map's "projected after" counts quantities: 7 + 5 units drafted is still under 2 days.
    assert [r["dest_cover_after_days"] for r in rows] == [0.5, 1.2, 7.5]
    assert rows[1]["src_on_hand_after"] == 995 and rows[1]["report_age_days"] == 0


def test_an_order_expired_while_being_signed_is_not_overwritten(monkeypatch):
    """Regression: a proposal expiring drafts mid-approval used to be overwritten back, or vice versa."""
    import backend.api.officer as officer
    from ml.data.facilities import load_facilities
    a, b = (f.facility_id for f in load_facilities(state="Maharashtra", district="Nashik")[:2])
    _order("o-race", a, b, "ors")
    real_sign = officer.sign

    def sign_while_a_proposal_expires_it(order, approved_by):
        live = factory.get("store_live")
        live.put("orders", order.order_id, order.model_copy(update={"status": OrderStatus.EXPIRED}))
        return real_sign(order, approved_by)

    monkeypatch.setattr(officer, "sign", sign_while_a_proposal_expires_it)
    response = TestClient(create_app()).post("/officer/orders/o-race/approve", headers=OFFICER)
    assert response.status_code == 409
    assert factory.get("store_live").get("orders", "o-race").status == OrderStatus.EXPIRED
