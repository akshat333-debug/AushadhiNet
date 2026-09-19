"""Hierarchical reconciliation: facility -> block -> district (modular-
plan.md §2.11). Bottom-up reconciliation, the simplest coherent method --
a district-level forecast is defined as the sum of its facility-level
forecasts, so drill-down views (the dashboard, project.md FR9) never show
inconsistent numbers between levels. MinT-diagonal is the natural upgrade
path if bottom-up variance pooling turns out to matter.
"""
from __future__ import annotations

import pandas as pd


def apply(
    forecast_df: pd.DataFrame,
    hierarchy: pd.DataFrame,
    group_by: tuple[str, ...] = ("drug_id",),
    value_cols: tuple[str, ...] = ("p50",),
) -> pd.DataFrame:
    """forecast_df: one row per facility_id (+ `group_by` keys, e.g.
    drug_id) with numeric columns in `value_cols`. hierarchy: [facility_id,
    block, district_id]. Returns a long frame [level, entity_id, *group_by,
    *value_cols] for level in {facility, block, district}; block/district
    rows are bottom-up sums of their children facilities."""
    df = forecast_df.merge(hierarchy[["facility_id", "block", "district_id"]], on="facility_id", how="left")

    facility_level = df[["facility_id", *group_by, *value_cols]].rename(columns={"facility_id": "entity_id"})
    facility_level["level"] = "facility"

    block_level = df.groupby(["block", *group_by], dropna=False)[list(value_cols)].sum().reset_index()
    block_level = block_level.rename(columns={"block": "entity_id"})
    block_level["level"] = "block"

    district_level = df.groupby(["district_id", *group_by], dropna=False)[list(value_cols)].sum().reset_index()
    district_level = district_level.rename(columns={"district_id": "entity_id"})
    district_level["level"] = "district"

    return pd.concat([facility_level, block_level, district_level], ignore_index=True, sort=False)
