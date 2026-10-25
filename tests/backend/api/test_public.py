"""DoD test for backend/api/public.py (step 36): aggregate only, no
facility-level identifiers."""
from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.domain import Confidence, ConfidenceSource, RecordStatus, StockRecord
from backend.providers import factory


def _seed_record(facility_id, drug_id, on_hand, record_id):
    record = StockRecord(
        record_id=record_id, facility_id=facility_id, drug_id=drug_id,
        reported_at=datetime.now(timezone.utc), as_of_date=date.today(), on_hand=on_hand,
        status=RecordStatus.CONFIRMED,
        confidence=Confidence(field_confidence={"on_hand": 1.0}, overall=1.0, source=ConfidenceSource.MANUAL),
        reporter_phone_hash="h1", raw_message_id="m1",
    )
    factory.get("store_live").put("stock_records", record_id, record)
    return record


def test_district_summary_returns_district_ids_not_facility_ids():
    real_facility_id = None
    from ml.data.facilities import load_facilities
    nashik_facility = load_facilities(state="Maharashtra", district="Nashik")[0]
    real_facility_id = nashik_facility.facility_id

    _seed_record(real_facility_id, "ors", on_hand=2, record_id="r1")

    client = TestClient(create_app())
    response = client.get("/public/district-summary")
    assert response.status_code == 200
    body = response.text
    assert real_facility_id not in body  # no facility-level identifier leaked
    data = response.json()
    assert any(row["district_id"] == "mh/nashik" for row in data)


def test_district_summary_counts_at_risk_facilities():
    from ml.data.facilities import load_facilities
    facs = load_facilities(state="Maharashtra", district="Nashik")[:2]
    _seed_record(facs[0].facility_id, "ors", on_hand=0, record_id="r2")          # under a week of cover
    _seed_record(facs[1].facility_id, "ors", on_hand=1_000_000, record_id="r3")  # well covered

    client = TestClient(create_app())
    data = client.get("/public/district-summary").json()
    nashik_row = next(row for row in data if row["district_id"] == "mh/nashik")
    assert nashik_row["facilities_at_risk"] == 1
    assert nashik_row["facilities_reporting"] == 2
    assert nashik_row["at_risk_by_drug"] == {"ors": 1}


def test_public_endpoint_requires_no_auth():
    client = TestClient(create_app())
    response = client.get("/public/district-summary")
    assert response.status_code == 200  # publicly accessible, per project.md's public role


def test_district_wide_gap_is_escalated_not_counted_as_a_transfer(monkeypatch):
    import backend.runtime as runtime
    from ml.data.facilities import load_facilities
    a, b, c = (f.facility_id for f in load_facilities(state="Maharashtra", district="Nashik")[:3])
    demand = {(a, "ors"): 10.0, (b, "ors"): 10.0, (a, "zinc-20mg"): 10.0, (c, "zinc-20mg"): 10.0}
    monkeypatch.setattr(runtime, "weekly_demand", lambda: demand)
    _seed_record(a, "ors", on_hand=0, record_id="e1")         # ORS: 5 in the district vs 20 needed
    _seed_record(b, "ors", on_hand=5, record_id="e2")
    _seed_record(a, "zinc-20mg", on_hand=0, record_id="e3")   # zinc: c holds plenty to move
    _seed_record(c, "zinc-20mg", on_hand=100, record_id="e4")

    row = next(r for r in TestClient(create_app()).get("/public/district-summary").json() if r["district_id"] == "mh/nashik")
    assert row["escalate"] == {"ors": 0.25}
    assert row["procurement_units"] == {"ors": 35}          # two weeks of 20 a week, less the 5 held
    assert row["facilities_at_risk"] == 2                    # a and b
    assert row["facilities_needing_transfer"] == 1           # only a, for zinc


def test_coverage_counts_states_without_naming_facilities():
    from ml.data.facilities import load_facilities
    nashik = load_facilities(state="Maharashtra", district="Nashik")[0]
    _seed_record(nashik.facility_id, "ors", on_hand=5, record_id="c1")
    response = TestClient(create_app()).get("/public/coverage")
    rows = {r["state"]: r for r in response.json()}
    assert "Andhra Pradesh Old" not in rows                  # pre-2014 duplicate of AP + Telangana
    assert rows["Maharashtra"]["live_districts"] == 1
    assert rows["Maharashtra"]["districts"] > 30 and rows["Uttar Pradesh"]["live_districts"] == 0
    assert nashik.name not in response.text
