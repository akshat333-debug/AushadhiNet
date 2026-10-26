"""Beds and staff end to end: WhatsApp reports in, the officer's summary and suggestions out."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.capacity import parse_beds, role_from
from backend.domain import StaffRole
from backend.providers import factory

PHONE = "whatsapp:+919800000221"  # MH-0000221, a CHC in Nashik (30 beds)
OFFICER = {"Authorization": "Bearer dev:o1:district:mh/nashik"}


@pytest.mark.parametrize("body, expected", [
    ("BEDS 4/6", (4, 6)), ("beds 4 of 6", (4, 6)), ("Beds: 12 30", (12, 30)), ("बेड ४/६", (4, 6)),
    ("ORS 50", None), ("BEDS 4", None),
])
def test_beds_message_parses(body, expected):
    assert parse_beds(body) == expected


def test_check_in_caption_names_the_role():
    assert role_from("MO checking in") == StaffRole.MO
    assert role_from("") == StaffRole.OTHER


def _send(client, **message):
    import uuid
    client.post("/simulator/message", json={"from_phone": PHONE, "message_id": uuid.uuid4().hex, **message})
    return client.get("/simulator/outbox", params={"phone": PHONE}).json()[-1]["body"]


def test_beds_report_is_recorded_and_replied_to():
    with TestClient(create_app()) as client:
        assert _send(client, body="BEDS 29/30") == "Beds recorded for MH-0000221: 29 of 30 occupied."
        assert _send(client, body="BEDS 31/30").startswith("Occupied beds cannot be more than total beds.")
        assert _send(client, body="BEDS 12/30", lang="hi") == "MH-0000221 के बेड दर्ज किए गए: 30 में से 12 भरे हैं।"
        census = factory.get("store_live").query("bed_census", {"facility_id": "MH-0000221"})
        assert sorted(c.beds_occupied for c in census) == [12, 29]


def test_shared_location_is_a_geofenced_check_in():
    from ml.data.facilities import served_facility_index
    f = served_facility_index()["MH-0000221"]
    with TestClient(create_app()) as client:
        assert _send(client, body="MO", latitude=f.lat, longitude=f.lon).startswith("Checked in at MH-0000221, ")
        assert _send(client, latitude=f.lat + 0.02, longitude=f.lon).startswith("Checked in, but you are 2.2 km from MH-0000221.")
    checkins = factory.get("store_live").query("checkins", {"facility_id": "MH-0000221"})
    assert sorted((c.role, c.geofence_ok) for c in checkins) == [(StaffRole.MO, True), (StaffRole.OTHER, False)]


def test_officer_sees_full_facilities_referrals_and_the_far_check_in():
    from ml.data.facilities import served_facility_index
    f = served_facility_index()["MH-0000221"]
    with TestClient(create_app()) as client:
        _send(client, body="BEDS 30/30")
        _send(client, latitude=f.lat + 0.05, longitude=f.lon)
        summary = client.get("/officer/capacity/mh/nashik", headers=OFFICER).json()
        assert client.get("/officer/capacity/mh/pune", headers=OFFICER).status_code == 403
    assert summary["demo_baseline"] is True
    assert summary["beds"]["full_count"] >= 1
    assert all(r["from_id"] != r["to_id"] and r["patients"] >= 1 for r in summary["beds"]["referrals"])
    assert summary["staff"]["off_site"][0] == {"facility_id": "MH-0000221", "name": f.name, "role": "other", "distance_m": 5560}


def test_deputation_moves_spare_staff_to_a_facility_with_nobody_on_site(monkeypatch):
    import backend.capacity as capacity
    chc = "MH-0000221"  # CHC: 3 MO posts, so one of three MOs present can be spared
    monkeypatch.setattr(capacity, "_baseline", lambda district, day: ({}, [
        {"facility_id": chc, "role": StaffRole.MO, "staff": f"mo{i}", "distance_m": 10.0} for i in range(3)]))
    with TestClient(create_app()) as client:
        staff = client.get("/officer/capacity/mh/nashik", headers=OFFICER).json()["staff"]
    assert staff["present"] == 3 and staff["nobody_count"] == staff["facilities"] - 1
    assert [(d["role"], d["staff"], d["from_id"]) for d in staff["deputations"]] == [("MO", 1, chc)]


def test_live_beds_replace_the_baseline_and_drive_referrals(monkeypatch):
    """Without the generated baseline, only reported facilities count, and a full one is referred to the nearest with room."""
    import backend.capacity as capacity
    from backend.config import get_settings
    monkeypatch.setattr(capacity, "_baseline", lambda district, day: ({}, []))
    from ml.data.facilities import load_facilities
    phcs = [f for f in load_facilities(state="Maharashtra", district="Nashik") if f.facility_type.value == "PHC"][:2]
    with TestClient(create_app()) as client:
        from backend.runtime import phone_for_facility
        for f, occupied in zip(phcs, (6, 1)):
            client.post("/simulator/message", json={"from_phone": phone_for_facility(f.facility_id), "body": f"BEDS {occupied}/6", "message_id": f"b{occupied}"})
        beds = client.get("/officer/capacity/mh/nashik", headers=OFFICER).json()["beds"]
    assert get_settings().mode == "local"
    assert (beds["facilities"], beds["occupied"], beds["total"], beds["full_count"]) == (2, 7, 12, 1)
    # 6/6 full: refer down to 80% (4 beds), the other PHC has room up to 80% (4 - 1 = 3)
    assert [(r["from_id"], r["to_id"], r["patients"]) for r in beds["referrals"]] == [(phcs[0].facility_id, phcs[1].facility_id, 2)]


def test_one_person_counts_once_stale_beds_are_unknown_and_live_check_ins_replace_the_baseline(monkeypatch):
    import backend.capacity as capacity
    from datetime import date, timedelta
    from ml.data.facilities import served_facility_index
    f = served_facility_index()["MH-0000221"]
    monkeypatch.setattr(capacity, "_baseline", lambda district, day: ({}, [
        {"facility_id": "MH-0000221", "role": StaffRole.MO, "staff": f"mo{i}", "distance_m": 10.0} for i in range(3)]))
    with TestClient(create_app()) as client:
        _send(client, latitude=f.lat, longitude=f.lon)
        _send(client, latitude=f.lat, longitude=f.lon)  # the same phone twice
        from backend.api.worker import handle_bed_census
        old = handle_bed_census({"message_sid": "old"}, "MH-0000221", beds_total=30, beds_occupied=30)
        live = factory.get("store_live")
        live.put("bed_census", old.record_id, old.model_copy(update={"as_of_date": date.today() - timedelta(days=30)}))
        summary = client.get("/officer/capacity/mh/nashik", headers=OFFICER).json()
    assert summary["staff"]["present"] == 1  # one live person; the 3 generated MOs no longer count
    assert summary["beds"]["facilities"] == 0  # a month-old census is not today's capacity
