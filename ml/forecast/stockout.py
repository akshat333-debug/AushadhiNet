"""Turns a demand forecast plus current stock into a stock-out probability
(modular-plan.md §2.11). Monotone by construction: for a fixed forecast
distribution, more on-hand stock can only lower or hold the probability
of running out, never raise it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def probability(forecast_df: pd.DataFrame, current_stock_df: pd.DataFrame, join_cols: list[str] | None = None) -> pd.DataFrame:
    """forecast_df: [..., p50, p10, p90] demand-over-horizon quantiles per
    entity/drug. current_stock_df: [..., on_hand] per entity/drug.
    Approximates the demand-over-horizon distribution as Normal(p50, sigma)
    with sigma implied by the p10/p90 spread, then returns
    P(demand > on_hand) = 1 - CDF(on_hand).
    """
    join_cols = join_cols or ["entity_id", "drug_id"]
    df = forecast_df.merge(current_stock_df, on=join_cols, how="left")

    # p10/p90 span ~2.563 std devs for a Normal distribution (z_0.9 - z_0.1)
    z_span = stats.norm.ppf(0.9) - stats.norm.ppf(0.1)
    sigma = ((df["p90"] - df["p10"]) / z_span).clip(lower=1e-6)

    df["stockout_prob"] = 1.0 - stats.norm.cdf(df["on_hand"], loc=df["p50"], scale=sigma)
    df["stockout_prob"] = df["stockout_prob"].clip(0.0, 1.0)
    return df


def is_monotone_in_stock(forecast_row: pd.Series, stock_levels: np.ndarray) -> bool:
    """Test helper: probability must be non-increasing as on_hand rises,
    for a fixed forecast distribution."""
    probs = []
    z_span = stats.norm.ppf(0.9) - stats.norm.ppf(0.1)
    sigma = max((forecast_row["p90"] - forecast_row["p10"]) / z_span, 1e-6)
    for stock in stock_levels:
        probs.append(1.0 - stats.norm.cdf(stock, loc=forecast_row["p50"], scale=sigma))
    return all(a >= b - 1e-9 for a, b in zip(probs, probs[1:]))
