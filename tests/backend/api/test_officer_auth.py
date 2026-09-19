"""DoD test for backend/api/officer.py (step 33)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.domain import BatchLine, OrderKind, OrderStatus, TransferOrder
from backend.providers import factory


def _client():
    return TestClient(create_app())


def _seed_order(order_id="o1", to_facility_id="F2"):
    order = TransferOrder(
        order_id=order_id, kind=OrderKind.DRUG_TRANSFER, from_facility_id="F1", to_facility_id=to_facility_id,
        drug_id="ors", quantity=10, batches=[BatchLine(batch_no="B1", quantity=10)],
        drive_minutes=25.0, rationale="test", created_at=datetime.now(timezone.utc), created_by="solver",
    )
    factory.get("store_live").put("orders", order_id, order)
    return order


def _auth(role: str, jurisdiction: str) -> dict:
    return {"Authorization": f"Bearer dev:u1:{role}:{jurisdiction}"}


def test_block_officer_cannot_approve_order_outside_their_jurisdiction():
    client = _client()
    _seed_order("o1")
    response = client.post("/officer/orders/o1/approve", params={"district_id": "hr/gurgaon"}, headers=_auth("district", "mh/nashik"))
    assert response.status_code == 403


def test_district_officer_can_approve_order_in_their_jurisdiction():
    client = _client()
    _seed_order("o2")
    response = client.post("/officer/orders/o2/approve", params={"district_id": "mh/nashik"}, headers=_auth("district", "mh"))
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["signature"] is not None


def test_approving_twice_is_idempotent():
    client = _client()
    _seed_order("o3")
    r1 = client.post("/officer/orders/o3/approve", params={"district_id": "mh/nashik"}, headers=_auth("district", "mh"))
    r2 = client.post("/officer/orders/o3/approve", params={"district_id": "mh/nashik"}, headers=_auth("district", "mh"))
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["signature"] == r2.json()["signature"]


def test_facility_role_cannot_approve_orders():
    client = _client()
    _seed_order("o4")
    response = client.post("/officer/orders/o4/approve", params={"district_id": "mh/nashik"}, headers=_auth("facility", "mh/nashik"))
    assert response.status_code == 403


def test_missing_order_returns_404():
    client = _client()
    response = client.post("/officer/orders/does-not-exist/approve", params={"district_id": "mh/nashik"}, headers=_auth("district", "mh"))
    assert response.status_code == 404


def test_reject_sets_status_rejected():
    client = _client()
    _seed_order("o5")
    response = client.post("/officer/orders/o5/reject", params={"district_id": "mh/nashik"}, headers=_auth("district", "mh"))
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_missing_auth_header_returns_401():
    client = _client()
    _seed_order("o6")
    response = client.post("/officer/orders/o6/approve", params={"district_id": "mh/nashik"})
    assert response.status_code == 401


def test_list_orders_matches_district_id_containing_a_slash():
    """Real bug found via Playwright e2e: FastAPI's default path
    converter does not match an embedded '/' in a path parameter, so
    GET /officer/orders/mh/nashik 404'd silently until the route used
    {district_id:path}."""
    client = _client()
    response = client.get("/officer/orders/mh/nashik", headers=_auth("district", "mh"))
    assert response.status_code == 200
    assert isinstance(response.json(), list)
