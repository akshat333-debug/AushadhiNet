"""DoD test for ml/forecast/service.py."""
from __future__ import annotations

import pandas as pd

from ml.forecast.service import latest_forecasts


def _panel():
    rows = []
    for i, week in enumerate(pd.date_range("2019-01-01", periods=6, freq="W-MON")):
        rows.append({"facility_id": "F1", "drug_id": "ors", "week": week,
                      "on_hand_open": 20 - i, "received": 0, "dispensed": 3, "unusable": 0,
                      "on_hand_close": 20 - i - 3})
    return pd.DataFrame(rows)


def test_returns_one_forecast_per_facility_drug():
    forecasts = latest_forecasts(["F1"], ["ors"], panel=_panel())
    assert len(forecasts) == 1
    f = forecasts[0]
    assert f.entity_id == "F1" and f.drug_id == "ors"
    assert f.p10 <= f.p50 <= f.p90
    assert 0.0 <= f.stockout_prob <= 1.0


def test_skips_facility_drug_with_insufficient_history():
    panel = _panel().iloc[:1]
    forecasts = latest_forecasts(["F1"], ["ors"], panel=panel)
    assert forecasts == []


def test_filters_to_requested_facilities_and_drugs():
    panel = pd.concat([_panel(), _panel().assign(facility_id="F2")])
    forecasts = latest_forecasts(["F1"], ["ors"], panel=panel)
    assert all(f.entity_id == "F1" for f in forecasts)
