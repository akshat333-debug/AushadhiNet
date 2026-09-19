"""DoD test for ml/forecast/stockout.py (step 19)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.forecast.stockout import is_monotone_in_stock, probability


def test_more_on_hand_lowers_or_holds_probability():
    row = pd.Series({"p10": 80.0, "p50": 100.0, "p90": 120.0})
    stock_levels = np.array([0, 50, 100, 150, 300])
    assert is_monotone_in_stock(row, stock_levels)


def test_probability_end_to_end():
    forecast_df = pd.DataFrame([
        {"entity_id": "F1", "drug_id": "ors", "p10": 80.0, "p50": 100.0, "p90": 120.0},
    ])
    stock_df = pd.DataFrame([{"entity_id": "F1", "drug_id": "ors", "on_hand": 100.0}])
    result = probability(forecast_df, stock_df)
    # on_hand == p50 -> roughly 50% chance of stocking out
    assert 0.4 < result.iloc[0]["stockout_prob"] < 0.6


def test_zero_stock_gives_high_probability():
    forecast_df = pd.DataFrame([{"entity_id": "F1", "drug_id": "ors", "p10": 80.0, "p50": 100.0, "p90": 120.0}])
    stock_df = pd.DataFrame([{"entity_id": "F1", "drug_id": "ors", "on_hand": 0.0}])
    result = probability(forecast_df, stock_df)
    assert result.iloc[0]["stockout_prob"] > 0.99


def test_huge_stock_gives_near_zero_probability():
    forecast_df = pd.DataFrame([{"entity_id": "F1", "drug_id": "ors", "p10": 80.0, "p50": 100.0, "p90": 120.0}])
    stock_df = pd.DataFrame([{"entity_id": "F1", "drug_id": "ors", "on_hand": 10000.0}])
    result = probability(forecast_df, stock_df)
    assert result.iloc[0]["stockout_prob"] < 0.01


def test_item_that_never_moves_is_not_at_risk_at_zero_stock():
    """Regression: 0 demand vs 0 stock used to read as a 50% stock-out risk."""
    forecast_df = pd.DataFrame([{"entity_id": "F1", "drug_id": "x", "p10": 0.0, "p50": 0.0, "p90": 0.0}])
    stock_df = pd.DataFrame([{"entity_id": "F1", "drug_id": "x", "on_hand": 0.0}])
    assert probability(forecast_df, stock_df).iloc[0]["stockout_prob"] < 0.01
