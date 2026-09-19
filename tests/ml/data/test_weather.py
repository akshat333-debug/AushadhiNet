"""DoD test for ml/data/weather.py (step 9)."""
from __future__ import annotations

import pandas as pd

from ml.data.weather import load_weather


def test_no_missing_days():
    df = load_weather()
    full_range = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    assert len(df) == len(full_range)
    assert set(df["date"]) == set(full_range)


def test_fill_value_becomes_nan_not_minus_999():
    df = load_weather()
    for col in ("rainfall_mm", "temp_c", "temp_max_c", "humidity_pct"):
        assert (df[col] == -999.0).sum() == 0


def test_covers_the_training_and_test_window():
    df = load_weather()
    assert df["date"].min() <= pd.Timestamp(2017, 4, 1)
    assert df["date"].max() >= pd.Timestamp(2020, 2, 29)
