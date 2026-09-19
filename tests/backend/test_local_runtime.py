"""The local demo loop through the real app startup: seed, WhatsApp report,
reply, confirmation, proposal, approval, alert."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.domain import RecordStatus
from backend.local_runtime import phone_for_facility
from backend.providers import factory

OFFICER = {"Authorization": "Bearer dev:o1:district:mh/nashik"}


def _send(client, phone, body, mid):
    return client.post("/simulator/message", json={"from_phone": phone, "body": body, "message_id": mid})


def _outbox(client, phone):
    return [m["body"] for m in client.get("/simulator/outbox", params={"phone": phone}).json()]


def test_startup_seeds_pilot_district():
    with TestClient(create_app()) as client:
        row = next(r for r in client.get("/public/district-summary").json() if r["district_id"] == "mh/nashik")
        assert row["facilities_reporting"] == 760


def test_text_report_is_recorded_and_acknowledged():
    with TestClient(create_app()) as client:
        facility_id = client.get("/simulator/contacts", params={"limit": 1}).json()[0]["facility_id"]
        phone = phone_for_facility(facility_id)
        _send(client, phone, "ORS 3", "m1")
        assert any("Recorded" in b and "ors 3" in b for b in _outbox(client, phone))
        detail = client.get(f"/officer/facility/{facility_id}", headers=OFFICER).json()
        assert any(s["drug_id"] == "ors" and s["on_hand"] == 3 for s in detail["stock"])


def test_unregistered_number_and_unreadable_text_get_replies():
    with TestClient(create_app()) as client:
        _send(client, "whatsapp:+10000000000", "ORS 3", "m2")
        assert _outbox(client, "whatsapp:+10000000000") == ["This number is not registered to a facility."]
        phone = phone_for_facility("MH-0000221")
        _send(client, phone, "hello", "m3")
        assert "Could not read that" in _outbox(client, phone)[-1]


def test_yes_confirms_pending_records():
    with TestClient(create_app()) as client:
        live = factory.get("store_live")
        record = next(iter(live.query("stock_records", {"facility_id": "MH-0000221"})))
        pending = record.model_copy(update={"record_id": "pending-1", "status": RecordStatus.PENDING})
        live.put("stock_records", "pending-1", pending)
        phone = phone_for_facility("MH-0000221")
        _send(client, phone, "YES", "m4")
        assert live.get("stock_records", "pending-1").status == RecordStatus.CONFIRMED
        assert _outbox(client, phone)[-1] == "Confirmed 1 record(s)."


def test_propose_then_approve_sends_alerts():
    with TestClient(create_app()) as client:
        drafts = client.post("/officer/propose/mh/nashik", headers=OFFICER).json()
        assert drafts and all(d["status"] == "draft" for d in drafts)
        listed = {o["order_id"] for o in client.get("/officer/orders/mh/nashik", headers=OFFICER).json()}
        assert {d["order_id"] for d in drafts} <= listed
        order = drafts[0]
        assert client.post(f"/officer/orders/{order['order_id']}/approve", headers=OFFICER).json()["status"] == "approved"
        assert _outbox(client, phone_for_facility(order["to_facility_id"]))


def test_second_proposal_supersedes_earlier_drafts():
    with TestClient(create_app()) as client:
        first = client.post("/officer/propose/mh/nashik", headers=OFFICER).json()
        second = client.post("/officer/propose/mh/nashik", headers=OFFICER).json()
        drafts = [o for o in client.get("/officer/orders/mh/nashik", headers=OFFICER).json() if o["status"] == "draft"]
        assert len(drafts) == len(second)
        assert factory.get("store_live").get("orders", first[0]["order_id"]).status.value == "expired"
