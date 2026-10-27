"""Referral and deputation suggestions become signed orders through the same approval path as transfers."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.domain import OrderKind, OrderStatus
from backend.providers import factory
from backend.runtime import phone_for_facility

OFFICER = {"Authorization": "Bearer dev:o1:district:mh/nashik"}


def test_approving_a_referral_signs_it_alerts_both_ends_and_marks_it_done():
    with TestClient(create_app()) as client:
        referral = client.get("/officer/capacity/mh/nashik", headers=OFFICER).json()["beds"]["referrals"][0]
        body = {"kind": "referral", "from_id": referral["from_id"], "to_id": referral["to_id"]}
        order = client.post("/officer/capacity/approve", json=body, headers=OFFICER).json()
        assert order["kind"] == "referral" and order["status"] == "approved" and order["signature"] and order["alerted_at"]
        assert order["patient_count"] == referral["patients"]
        for fid in (referral["from_id"], referral["to_id"]):
            outbox = client.get("/simulator/outbox", params={"phone": phone_for_facility(fid)}).json()
            assert any("Patients referred" in m["body"] for m in outbox)
        again = client.get("/officer/capacity/mh/nashik", headers=OFFICER).json()["beds"]["referrals"]
        assert next(r for r in again if r["from_id"] == referral["from_id"] and r["to_id"] == referral["to_id"])["order_id"] == order["order_id"]
        assert client.post("/officer/capacity/approve", json=body, headers=OFFICER).json()["order_id"] == order["order_id"]  # idempotent


def test_deputation_approval_and_stale_or_foreign_suggestions_are_refused():
    with TestClient(create_app()) as client:
        dep = client.get("/officer/capacity/mh/nashik", headers=OFFICER).json()["staff"]["deputations"][0]
        body = {"kind": "deputation", "from_id": dep["from_id"], "to_id": dep["to_id"], "role": dep["role"]}
        order = client.post("/officer/capacity/approve", json=body, headers=OFFICER).json()
        stored = factory.get("store_live").get("orders", order["order_id"])
        assert stored.kind == OrderKind.DEPUTATION and stored.status == OrderStatus.APPROVED
        assert (stored.role, stored.staff_count) == (dep["role"], dep["staff"])
        from backend.action.sign_order import verify
        assert verify(stored) and not verify(stored.model_copy(update={"role": "Pharmacist", "staff_count": 9}))  # the instruction is signed
        wrong_role = {**body, "role": "nobody"}
        assert client.post("/officer/capacity/approve", json=wrong_role, headers=OFFICER).status_code == 409
        made_up = {"kind": "referral", "from_id": dep["to_id"], "to_id": dep["from_id"]}
        assert client.post("/officer/capacity/approve", json=made_up, headers=OFFICER).status_code == 409
        dhule = {"Authorization": "Bearer dev:o2:district:mh/dhule"}
        assert client.post("/officer/capacity/approve", json=body, headers=dhule).status_code == 403


def test_approved_moves_count_where_they_went():
    """Patients referred leave the source's beds; a deputed person is not suggested again."""
    with TestClient(create_app()) as client:
        cap = client.get("/officer/capacity/mh/nashik", headers=OFFICER).json()
        referral, dep = cap["beds"]["referrals"][0], cap["staff"]["deputations"][0]
        before = next(f for f in cap["beds"]["full"] if f["facility_id"] == referral["from_id"])
        client.post("/officer/capacity/approve", json={"kind": "referral", "from_id": referral["from_id"], "to_id": referral["to_id"]}, headers=OFFICER)
        client.post("/officer/capacity/approve", json={"kind": "deputation", "from_id": dep["from_id"], "to_id": dep["to_id"], "role": dep["role"]}, headers=OFFICER)
        after = client.get("/officer/capacity/mh/nashik", headers=OFFICER).json()
        still_full = [f for f in after["beds"]["full"] if f["facility_id"] == referral["from_id"]]
        assert not still_full or still_full[0]["occupied"] == before["occupied"] - referral["patients"]
        assert after["beds"]["occupied"] == cap["beds"]["occupied"]  # moved, not discharged
        open_to_same_place = [d for d in after["staff"]["deputations"]
                              if d["to_id"] == dep["to_id"] and d["role"] == dep["role"] and not d["order_id"]]
        assert not open_to_same_place  # the gap is covered
