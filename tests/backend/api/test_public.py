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
    _seed_record(facs[0].facility_id, "ors-new-who", on_hand=0, record_id="r2")          # under a week of cover
    _seed_record(facs[1].facility_id, "ors-new-who", on_hand=1_000_000, record_id="r3")  # well covered

    client = TestClient(create_app())
    data = client.get("/public/district-summary").json()
    nashik_row = next(row for row in data if row["district_id"] == "mh/nashik")
    assert nashik_row["facilities_at_risk"] == 1
    assert nashik_row["facilities_reporting"] == 2
    assert nashik_row["at_risk_by_drug"] == {"ors-new-who": 1}


def test_public_endpoint_requires_no_auth():
    client = TestClient(create_app())
    response = client.get("/public/district-summary")
    assert response.status_code == 200  # publicly accessible, per project.md's public role
