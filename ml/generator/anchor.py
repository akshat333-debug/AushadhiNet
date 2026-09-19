"""Rescales the observable base demand shape so district-month totals match
real HMIS M19 "Stock Distributed" figures (modular-plan.md §2.8).

Expects `anchors` already resolved to drug_id (cli.py is responsible for
mapping HMIS drug_name -> drug_id via ml/data/drugs.py aliases before
calling this). Where no real anchor exists for a (district, drug, month)
combination, the unscaled base shape is kept and `anchored=False` is
recorded, so callers can see exactly how much of the ledger is
real-anchored versus shape-only.
"""
from __future__ import annotations

import pandas as pd


def scale_to_anchor(
    base_shape: pd.DataFrame,
    facility_district: dict[str, str],
    anchors: pd.DataFrame | None,
) -> pd.DataFrame:
    """base_shape: facility_id, drug_id, week, base_intensity.
    anchors: district_id, drug_id, month (Timestamp, first-of-month), distributed.
    Returns facility_id, drug_id, week, target_dispense, anchored (bool).
    """
    df = base_shape.copy()
    df["district_id"] = df["facility_id"].map(facility_district)
    df["month"] = df["week"].dt.to_period("M").dt.to_timestamp()

    if anchors is None or anchors.empty:
        df["target_dispense"] = df["base_intensity"]
        df["anchored"] = False
        return df.drop(columns=["district_id", "month"])

    group_sum = df.groupby(["district_id", "drug_id", "month"])["base_intensity"].transform("sum")
    df["_group_sum"] = group_sum

    anchor_cols = anchors[["district_id", "drug_id", "month", "distributed"]].drop_duplicates(
        subset=["district_id", "drug_id", "month"]
    )
    df = df.merge(anchor_cols, on=["district_id", "drug_id", "month"], how="left")

    has_anchor = df["distributed"].notna() & (df["_group_sum"] > 0)
    scale = pd.Series(1.0, index=df.index)
    scale.loc[has_anchor] = df.loc[has_anchor, "distributed"] / df.loc[has_anchor, "_group_sum"]

    df["target_dispense"] = df["base_intensity"] * scale
    df["anchored"] = has_anchor
    return df.drop(columns=["district_id", "month", "_group_sum", "distributed"])
