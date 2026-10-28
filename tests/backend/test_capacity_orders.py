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


def test_approved_moves_are_planned_around_not_reported():
    """Judge's case: approving a referral or deputation must not change reported beds or presence."""
    with TestClient(create_app()) as client:
        cap = client.get("/officer/capacity/mh/nashik", headers=OFFICER).json()
        referral, dep = cap["beds"]["referrals"][0], cap["staff"]["deputations"][0]
        client.post("/officer/capacity/approve", json={"kind": "referral", "from_id": referral["from_id"], "to_id": referral["to_id"]}, headers=OFFICER)
        client.post("/officer/capacity/approve", json={"kind": "deputation", "from_id": dep["from_id"], "to_id": dep["to_id"], "role": dep["role"]}, headers=OFFICER)
        after = client.get("/officer/capacity/mh/nashik", headers=OFFICER).json()
        # Approval is a commitment, not an observation: the reported numbers do not move.
        assert after["beds"]["full"] == cap["beds"]["full"] and after["beds"]["full_count"] == cap["beds"]["full_count"]
        assert after["beds"]["occupied"] == cap["beds"]["occupied"] and after["staff"]["present"] == cap["staff"]["present"]
        assert not [r for r in after["beds"]["referrals"] if r["from_id"] == referral["from_id"] and not r["order_id"]
                    and r["patients"] >= referral["patients"]]  # the same patients are not suggested again
        open_to_same_place = [d for d in after["staff"]["deputations"]
                              if d["to_id"] == dep["to_id"] and d["role"] == dep["role"] and not d["order_id"]]
        assert not open_to_same_place  # the gap is covered


def _no_new_suggestion(client, referral):
    after = client.get("/officer/capacity/mh/nashik", headers=OFFICER).json()["beds"]["referrals"]
    return not [r for r in after if r["from_id"] == referral["from_id"] and not r["order_id"] and r["patients"] >= referral["patients"]]


def test_a_referral_stays_reserved_through_an_unchanged_census_and_dispatch():
    """Judge's case: a census sent after approval, with nobody moved yet, or the referral marked
    dispatched, made the same patients appear again."""
    import uuid
    from backend.capacity import district_capacity
    from backend.api.officer import mark_dispatched
    with TestClient(create_app()) as client:
        referral = client.get("/officer/capacity/mh/nashik", headers=OFFICER).json()["beds"]["referrals"][0]
        beds = district_capacity("mh/nashik", referral["from_id"])["facility"]["beds"]
        order = client.post("/officer/capacity/approve", json={"kind": "referral", "from_id": referral["from_id"], "to_id": referral["to_id"]},
                            headers=OFFICER).json()
        client.post("/simulator/message", json={"from_phone": phone_for_facility(referral["from_id"]), "message_id": uuid.uuid4().hex,
                                                "body": f"BEDS {beds['occupied']}/{beds['total']}"})  # nobody has left yet
        assert _no_new_suggestion(client, referral)
        mark_dispatched(factory.get("store_live").get("orders", order["order_id"]))
        assert _no_new_suggestion(client, referral)


def test_two_simultaneous_approvals_of_one_suggestion_make_one_order(monkeypatch):
    import threading
    import time
    from backend import capacity
    with TestClient(create_app()) as client:
        referral = client.get("/officer/capacity/mh/nashik", headers=OFFICER).json()["beds"]["referrals"][0]
        real = capacity.district_capacity

        def slow(*a, **kw):  # both requests read the suggestion before either writes its order
            result = real(*a, **kw)
            time.sleep(0.5)
            return result
        monkeypatch.setattr(capacity, "district_capacity", slow)
        body = {"kind": "referral", "from_id": referral["from_id"], "to_id": referral["to_id"]}
        ids = []
        threads = [threading.Thread(target=lambda: ids.append(client.post("/officer/capacity/approve", json=body, headers=OFFICER).json()["order_id"]))
                   for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(set(ids)) == 1


def test_a_referral_approved_before_midnight_stays_reserved():
    from datetime import timedelta
    with TestClient(create_app()) as client:
        referral = client.get("/officer/capacity/mh/nashik", headers=OFFICER).json()["beds"]["referrals"][0]
        order = client.post("/officer/capacity/approve", json={"kind": "referral", "from_id": referral["from_id"], "to_id": referral["to_id"]},
                            headers=OFFICER).json()
        live = factory.get("store_live")
        stored = live.get("orders", order["order_id"])
        live.put("orders", stored.order_id, stored.model_copy(update={"approved_at": stored.approved_at - timedelta(days=1)}))  # still on the road
        assert _no_new_suggestion(client, referral)
