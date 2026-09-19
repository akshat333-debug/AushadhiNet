"""The one function the rest of the system calls for forecasts (modular-
plan.md §2.11's file list; the numbered implementation order omitted a
dedicated step for it, so it is added here alongside ml/optimize/, which
is its first real caller).
"""
from __future__ import annotations

import uuid
from datetime import date

import numpy as np
import pandas as pd

from backend.domain import Forecast, Grain

from ml.data.panel import build as build_panel
from ml.forecast.baselines import seasonal_naive
from ml.forecast.stockout import probability as stockout_probability


def latest_forecasts(
    facility_ids: list[str],
    drug_ids: list[str],
    horizon_weeks: int = 4,
    panel: pd.DataFrame | None = None,
) -> list[Forecast]:
    """Facility x drug demand forecasts at FACILITY_WEEK grain, using
    lag-1 naive. LightGBM wins at DISTRICT_MONTH grain but loses here
    (last 13 train weeks: naive 0.243 WAPE, best LightGBM variant 0.255),
    see TASK.md.
    """
    panel = panel if panel is not None else build_panel(Grain.FACILITY_WEEK)
    subset = panel[panel["facility_id"].isin(facility_ids) & panel["drug_id"].isin(drug_ids)]

    forecasts: list[Forecast] = []
    for (facility_id, drug_id), group in subset.groupby(["facility_id", "drug_id"]):
        group = group.sort_values("week")
        history = group["dispensed"].to_numpy()
        if len(history) < 2:
            continue
        p50 = float(seasonal_naive(pd.Series(history), horizon=1, season_length=1)[0])
        spread = max(float(np.std(history[-8:])), 1.0)
        p10, p90 = max(0.0, p50 - 1.2816 * spread), p50 + 1.2816 * spread

        on_hand = float(group["on_hand_close"].iloc[-1])
        prob_df = stockout_probability(
            pd.DataFrame([{"entity_id": facility_id, "drug_id": drug_id, "p10": p10, "p50": p50, "p90": p90}]),
            pd.DataFrame([{"entity_id": facility_id, "drug_id": drug_id, "on_hand": on_hand}]),
        )
        stockout_prob = float(prob_df.iloc[0]["stockout_prob"])

        forecasts.append(Forecast(
            forecast_id=str(uuid.uuid4()), grain=Grain.FACILITY_WEEK, entity_id=facility_id,
            drug_id=drug_id, origin_date=group["week"].max().date(), horizon=horizon_weeks,
            p50=p50, p10=p10, p90=p90, stockout_prob=stockout_prob,
            model="seasonal_naive", model_version="0.1", features_hash="n/a",
        ))
    return forecasts
