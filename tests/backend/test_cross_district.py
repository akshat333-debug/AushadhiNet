"""Cross-district redistribution: a state-wide proposal moves surplus from one district to a
shortage in the next, and only an officer covering both districts can approve it."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pandas as pd
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.domain import Confidence, ConfidenceSource, RecordStatus, StockRecord
from backend.providers import factory

NASHIK, DHULE = "MH-0011099", "MH-0011117"  # neighbouring facilities across the district line


def _panel() -> pd.DataFrame:
    weeks = [pd.Timestamp("2026-08-03") + timedelta(weeks=i) for i in range(8)]
    return pd.DataFrame([{"facility_id": f, "drug_id": "ors", "week": w, "on_hand_open": 0.0, "received": 0.0,
                          "dispensed": 70.0, "unusable": 0.0, "on_hand_close": 0.0} for f in (NASHIK, DHULE) for w in weeks])


def _stock(facility_id: str, on_hand: int) -> None:
    factory.get("store_live").put("stock_records", f"s-{facility_id}", StockRecord(
        record_id=f"s-{facility_id}", facility_id=facility_id, drug_id="ors", reported_at=datetime.now(timezone.utc),
        as_of_date=date.today(), on_hand=on_hand, status=RecordStatus.CONFIRMED,
        confidence=Confidence(field_confidence={"on_hand": 1.0}, overall=1.0, source=ConfidenceSource.MANUAL),
        reporter_phone_hash="h", raw_message_id="m"))


def test_state_proposal_crosses_the_district_line_and_needs_a_state_officer(monkeypatch):
    import backend.runtime as runtime
    monkeypatch.setattr(runtime, "forecast_panel", _panel)
    _stock(NASHIK, 0)
    _stock(DHULE, 2000)
    client = TestClient(create_app())

    district = {"Authorization": "Bearer dev:o1:district:mh/nashik"}
    state = {"Authorization": "Bearer dev:s1:state:mh"}
    assert client.post("/officer/propose/mh/nashik", headers=district).json() == []  # no surplus inside Nashik

    drafts = client.post("/officer/propose/mh", headers=state).json()
    assert [(d["from_facility_id"], d["to_facility_id"]) for d in drafts] == [(DHULE, NASHIK)]
    order_id = drafts[0]["order_id"]
    assert order_id in [o["order_id"] for o in client.get("/officer/orders/mh/nashik", headers=district).json()]

    assert client.post(f"/officer/orders/{order_id}/approve", headers=district).status_code == 403
    assert client.post(f"/officer/orders/{order_id}/approve", headers=state).status_code == 200
