"""The one function the rest of the system calls for forecasts (modular-
plan.md §2.11's file list; the numbered implementation order omitted a
dedicated step for it, so it is added here alongside ml/optimize/, which
is its first real caller).
"""
from __future__ import annotations

import uuid

import pandas as pd

from backend.domain import Forecast, Grain

from ml.data.panel import build as build_panel
from ml.forecast.stockout import probability as stockout_probability


def latest_forecasts(
    facility_ids: list[str],
    drug_ids: list[str],
    horizon_weeks: int = 1,
    panel: pd.DataFrame | None = None,
    on_hand: dict[tuple[str, str], float] | None = None,
) -> list[Forecast]:
    """Next-week facility x drug demand forecasts at FACILITY_WEEK grain,
    using lag-1 naive. LightGBM wins at DISTRICT_MONTH grain but loses here
    (last 13 train weeks: naive 0.220 WAPE, best LightGBM variant 0.239),
    see TASK.md. `on_hand` overrides the ledger's closing stock with live
    reports when given, so a new WhatsApp report changes the risk.
    """
    panel = panel if panel is not None else build_panel(Grain.FACILITY_WEEK)
    subset = panel[panel["facility_id"].isin(facility_ids) & panel["drug_id"].isin(drug_ids)].sort_values("week")
    grouped = subset.groupby(["facility_id", "drug_id"])
    stats = grouped.agg(
        n=("dispensed", "size"), p50=("dispensed", "last"),
        spread=("dispensed", lambda s: s.iloc[-8:].std(ddof=0)),
        ledger_on_hand=("on_hand_close", "last"), origin=("week", "max"),
    ).reset_index()
    stats = stats[stats["n"] >= 2]
    if stats.empty:
        return []

    stats["spread"] = stats["spread"].fillna(0.0)
    stats["p10"] = (stats["p50"] - 1.2816 * stats["spread"]).clip(lower=0.0)
    stats["p90"] = stats["p50"] + 1.2816 * stats["spread"]
    live = on_hand or {}
    stats["on_hand"] = [live.get((f, d), l) for f, d, l in zip(stats["facility_id"], stats["drug_id"], stats["ledger_on_hand"])]
    probs = stockout_probability(
        stats.rename(columns={"facility_id": "entity_id"})[["entity_id", "drug_id", "p10", "p50", "p90"]],
        stats.rename(columns={"facility_id": "entity_id"})[["entity_id", "drug_id", "on_hand"]],
    )["stockout_prob"].to_numpy()

    return [
        Forecast(
            forecast_id=str(uuid.uuid4()), grain=Grain.FACILITY_WEEK, entity_id=row.facility_id,
            drug_id=row.drug_id, origin_date=row.origin.date(), horizon=horizon_weeks,
            p50=float(row.p50), p10=float(row.p10), p90=float(row.p90), stockout_prob=float(prob),
            model="seasonal_naive", model_version="0.1", features_hash="n/a",
        )
        for row, prob in zip(stats.itertuples(), probs)
    ]
