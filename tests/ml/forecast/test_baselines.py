"""DoD test for ml/forecast/features.py + baselines.py (step 14)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.domain import Grain
from ml.forecast.baselines import moving_average, seasonal_naive
from ml.forecast.features import add_calendar_features, add_lag_features, build_features, feature_columns


def test_seasonal_naive_reproduces_sine_exactly():
    t = np.arange(24)
    values = np.round(10 + 5 * np.sin(2 * np.pi * t / 12), 4)  # period-12 seasonal series
    history = pd.Series(values[:12])
    forecast = seasonal_naive(history, horizon=12, season_length=12)
    np.testing.assert_allclose(forecast, values[:12])


def test_seasonal_naive_season_length_1_is_last_value_carried_forward():
    history = pd.Series([1, 2, 3, 4, 5])
    forecast = seasonal_naive(history, horizon=3, season_length=1)
    np.testing.assert_allclose(forecast, [5, 5, 5])


def test_moving_average_hand_computed():
    history = pd.Series([10, 20, 30, 40])
    forecast = moving_average(history, horizon=2, window=3)
    np.testing.assert_allclose(forecast, [30, 30])  # mean(20,30,40)=30


def test_moving_average_rejects_empty_history():
    with pytest.raises(ValueError):
        moving_average(pd.Series([], dtype=float), horizon=1)


# --- features ---

def _toy_panel():
    rows = []
    for month in pd.date_range("2019-01-01", periods=4, freq="MS"):
        rows.append({"district_id": "mh/nashik", "state_code": "MH", "drug_name": "ORS",
                      "month": month, "distributed": 100.0, "balance_prev": 50.0,
                      "received": 20.0, "unusable": 1.0, "total": 69.0,
                      "opd_attendance": 500, "inpatient_midnight_census": 30, "institutional_deliveries": 10})
    return pd.DataFrame(rows)


def test_lag_features_shift_by_entity_and_never_leak_same_period():
    panel = _toy_panel()
    df = add_lag_features(panel, Grain.DISTRICT_MONTH, lags=(1,))
    # the raw same-period columns must be gone
    assert "distributed" not in df.columns
    # first row has no history -> lag is NaN
    assert pd.isna(df.iloc[0]["distributed_lag1"])
    # second row's lag1 equals the first row's original value
    assert df.iloc[1]["distributed_lag1"] == 100.0


def test_calendar_features_flag_monsoon_months():
    panel = _toy_panel()
    df = add_calendar_features(panel, Grain.DISTRICT_MONTH)
    jan_row = df[df["month"] == pd.Timestamp("2019-01-01")].iloc[0]
    assert jan_row["is_monsoon"] == 0
    df2 = add_calendar_features(panel.assign(month=pd.to_datetime(["2019-07-01"] * 4)), Grain.DISTRICT_MONTH)
    assert (df2["is_monsoon"] == 1).all()


def test_build_features_reattaches_target_without_leaking_it_as_a_feature():
    panel = _toy_panel()
    df = build_features(panel, Grain.DISTRICT_MONTH, target_col="distributed")
    assert "distributed" in df.columns  # target present for supervision
    cols = feature_columns(df, target_col="distributed")
    assert "distributed" not in cols
    assert "distributed_lag1" in cols  # lagged version is a valid feature
    assert all(not c.endswith("_lag0") for c in cols)


def test_feature_columns_is_stable_and_sorted():
    panel = _toy_panel()
    df = build_features(panel, Grain.DISTRICT_MONTH, target_col="distributed")
    cols1 = feature_columns(df, target_col="distributed")
    cols2 = feature_columns(df.sample(frac=1, random_state=0), target_col="distributed")
    assert cols1 == cols2
    assert list(cols1) == sorted(cols1)
