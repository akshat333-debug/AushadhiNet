"""DoD test for ml/optimize/service.py."""
from __future__ import annotations

import pandas as pd

from backend.domain import Facility, FacilityType
from ml.optimize.service import propose


def test_propose_returns_draft_orders_from_end_to_end_forecast(monkeypatch):
    facilities = [
        Facility(facility_id="F1", name="A", state_code="MH", district_id="mh/nashik",
                  facility_type=FacilityType.PHC, lat=20.0, lon=73.8),
        Facility(facility_id="F2", name="B", state_code="MH", district_id="mh/nashik",
                  facility_type=FacilityType.PHC, lat=20.05, lon=73.85),
    ]

    def fake_forecasts(facility_ids, drug_ids, horizon_weeks=4, panel=None):
        from backend.domain import Forecast, Grain
        return [
            Forecast(forecast_id="f1", grain=Grain.FACILITY_WEEK, entity_id="F1", drug_id="ors",
                      origin_date=pd.Timestamp("2019-06-01").date(), horizon=4,
                      p50=50.0, p10=40.0, p90=60.0, stockout_prob=0.9,
                      model="test", model_version="0", features_hash="x"),
            Forecast(forecast_id="f2", grain=Grain.FACILITY_WEEK, entity_id="F2", drug_id="ors",
                      origin_date=pd.Timestamp("2019-06-01").date(), horizon=4,
                      p50=50.0, p10=40.0, p90=60.0, stockout_prob=0.05,
                      model="test", model_version="0", features_hash="x"),
        ]

    monkeypatch.setattr("ml.optimize.service.latest_forecasts", fake_forecasts)

    orders = propose(
        facilities=facilities, drug_ids=["ors"], cold_chain_by_drug={"ors": False},
        stock_by_facility_drug={("F1", "ors"): 5.0, ("F2", "ors"): 200.0},
    )
    assert len(orders) == 1
    assert orders[0].from_facility_id == "F2"
    assert orders[0].to_facility_id == "F1"
    assert orders[0].status.value == "draft"


def test_propose_returns_empty_when_no_risk():
    facilities = [
        Facility(facility_id="F1", name="A", state_code="MH", district_id="mh/nashik",
                  facility_type=FacilityType.PHC, lat=20.0, lon=73.8),
    ]
    orders = propose(facilities, ["ors"], {"ors": False}, {})
    assert orders == []
