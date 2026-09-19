"""Officer API authorisation: jurisdiction comes from the order's own
facilities, never from a caller-supplied district."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.domain import BatchLine, OrderKind, OrderStatus, TransferOrder
from backend.providers import factory

NASHIK_A, NASHIK_B, DHULE, WARDHA = "MH-0000221", "MH-0000223", "MH-0000337", "MH-0000338"


def _client():
    return TestClient(create_app())


def _seed_order(order_id="o1", from_id=NASHIK_A, to_id=NASHIK_B):
    order = TransferOrder(
        order_id=order_id, kind=OrderKind.DRUG_TRANSFER, from_facility_id=from_id, to_facility_id=to_id,
        drug_id="ors-new-who", quantity=10, batches=[BatchLine(batch_no="B1", quantity=10)],
        drive_minutes=25.0, rationale="test", created_at=datetime.now(timezone.utc), created_by="solver",
    )
    factory.get("store_live").put("orders", order_id, order)
    return order


def _auth(role: str, jurisdiction: str) -> dict:
    return {"Authorization": f"Bearer dev:u1:{role}:{jurisdiction}"}


def test_officer_cannot_approve_other_district_order_by_naming_own_district():
    """Regression: approval used to trust a caller-supplied district_id."""
    client = _client()
    _seed_order("o1")
    response = client.post("/officer/orders/o1/approve", params={"district_id": "mh/dhule"}, headers=_auth("district", "mh/dhule"))
    assert response.status_code == 403
    assert factory.get("store_live").get("orders", "o1").status == OrderStatus.DRAFT


def test_cross_district_order_needs_both_districts():
    client = _client()
    _seed_order("ox", from_id=DHULE, to_id=NASHIK_A)
    assert client.post("/officer/orders/ox/approve", headers=_auth("district", "mh/nashik")).status_code == 403
    assert client.post("/officer/orders/ox/approve", headers=_auth("state", "mh")).status_code == 200


def test_district_officer_can_approve_order_in_their_jurisdiction():
    client = _client()
    _seed_order("o2")
    response = client.post("/officer/orders/o2/approve", headers=_auth("district", "mh/nashik"))
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["signature"] is not None


def test_approval_alerts_both_facilities():
    from backend.local_runtime import phone_for_facility
    client = _client()
    _seed_order("oa")
    client.post("/officer/orders/oa/approve", headers=_auth("district", "mh"))
    recipients = {m.to for m in factory.get("messaging").sent}
    assert {phone_for_facility(NASHIK_A), phone_for_facility(NASHIK_B)} <= recipients


def test_approving_twice_is_idempotent():
    client = _client()
    _seed_order("o3")
    r1 = client.post("/officer/orders/o3/approve", headers=_auth("district", "mh"))
    sent_after_first = len(factory.get("messaging").sent)
    r2 = client.post("/officer/orders/o3/approve", headers=_auth("district", "mh"))
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["signature"] == r2.json()["signature"]
    assert len(factory.get("messaging").sent) == sent_after_first  # no duplicate alerts


def test_approved_order_cannot_be_rejected():
    client = _client()
    _seed_order("o7")
    client.post("/officer/orders/o7/approve", headers=_auth("district", "mh"))
    response = client.post("/officer/orders/o7/reject", headers=_auth("district", "mh"))
    assert response.status_code == 409
    assert factory.get("store_live").get("orders", "o7").status == OrderStatus.APPROVED


def test_facility_role_cannot_approve_orders():
    client = _client()
    _seed_order("o4")
    response = client.post("/officer/orders/o4/approve", headers=_auth("facility", "mh/nashik"))
    assert response.status_code == 403


def test_missing_order_returns_404():
    client = _client()
    response = client.post("/officer/orders/does-not-exist/approve", headers=_auth("district", "mh"))
    assert response.status_code == 404


def test_reject_sets_status_rejected():
    client = _client()
    _seed_order("o5")
    response = client.post("/officer/orders/o5/reject", headers=_auth("district", "mh"))
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_missing_auth_header_returns_401():
    client = _client()
    _seed_order("o6")
    response = client.post("/officer/orders/o6/approve")
    assert response.status_code == 401


def test_list_orders_is_scoped_to_district():
    client = _client()
    _seed_order("in-nashik")
    _seed_order("in-dhule", from_id=DHULE, to_id=WARDHA)
    ids = {o["order_id"] for o in client.get("/officer/orders/mh/nashik", headers=_auth("district", "mh")).json()}
    assert "in-nashik" in ids and "in-dhule" not in ids


def test_list_orders_rejects_other_jurisdiction():
    client = _client()
    assert client.get("/officer/orders/mh/nashik", headers=_auth("district", "mh/dhule")).status_code == 403


def test_facility_detail_is_jurisdiction_checked():
    client = _client()
    assert client.get(f"/officer/facility/{DHULE}", headers=_auth("district", "mh/nashik")).status_code == 403
