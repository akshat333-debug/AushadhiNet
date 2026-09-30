"""Assembles the modelling panel at a given Grain (modular-plan.md §1's
Grain resolution, and §2.9 step 12). This module ASSEMBLES real and
synthetic sources into one table per grain; it does not engineer lagged
features or decide what a forecaster may causally use -- that is
ml/forecast/features.py's job (step 14). panel.py's only leakage
responsibility is temporal: an optional `cutoff` truncates the panel so a
caller building a training set cannot accidentally include rows dated
after it.

Reads data/synthetic/*.parquet directly for FACILITY_WEEK (the sealed
generator's *output* files, not the generator module itself -- this does
not violate the ml.generator import isolation rule; see
tests/test_isolation.py and data/README.md).
"""
from __future__ import annotations

import pathlib
from datetime import date

import pandas as pd

from backend.domain import Grain

from ml.data.hmis_m19 import load_m19
from ml.data.hmis_service import load_service_indicators

SYNTHETIC_DIR = pathlib.Path(__file__).resolve().parents[2] / "data" / "synthetic"

# "Required" means these are the panel's join keys / identity columns --
# they must never be NaN, or a row is meaningless. The real-data HMIS
# measurement columns (balance_prev, received, unusable, distributed,
# total) are deliberately NOT in this list: ~12-15% of district-month-drug
# combinations are genuinely unreported in the source data (a real
# last-mile reporting gap, not a parsing bug -- this IS the problem the
# project exists to fix). ml/forecast/features.py, not panel.py, decides
# how to handle that missingness (impute, drop, or treat as a feature).
REQUIRED_COLUMNS = {
    Grain.DISTRICT_MONTH: ["district_id", "state_code", "drug_name", "month"],
    Grain.FACILITY_WEEK: [
        "facility_id", "drug_id", "week",
        "on_hand_open", "received", "dispensed", "unusable", "on_hand_close",
    ],
}


def _cutoff_column(grain: Grain) -> str:
    return "month" if grain == Grain.DISTRICT_MONTH else "week"


def build(
    grain: Grain,
    states: list[str] | None = None,
    cutoff: date | None = None,
    synthetic_dir: pathlib.Path = SYNTHETIC_DIR,
    since: date | None = None,
) -> pd.DataFrame:
    """Assemble the panel for `grain`. `cutoff` (inclusive), if given,
    drops every row dated after it -- the mechanism a training-only caller
    (e.g. eval/run_backtest.py) uses to guarantee it never sees the test
    window (architecture.md §5).

    `since` (exclusive) is the opposite end, pushed down into the parquet read
    so a serving process never materialises the whole ledger."""
    if grain == Grain.DISTRICT_MONTH:
        df = load_m19(states=states)
        service = load_service_indicators(states=states)
        df = df.merge(service, on=["state_code", "district_id", "month"], how="left")
    elif grain == Grain.FACILITY_WEEK:
        filters = [("week", ">", pd.Timestamp(since))] if since is not None else None
        df = pd.read_parquet(synthetic_dir / "stock.parquet", filters=filters, columns=list(REQUIRED_COLUMNS[grain]))
    else:
        raise ValueError(f"unknown grain: {grain}")

    required = REQUIRED_COLUMNS[grain]
    missing_required = [c for c in required if c not in df.columns]
    if missing_required:
        raise ValueError(f"panel is missing required columns for {grain}: {missing_required}")

    if cutoff is not None:
        col = _cutoff_column(grain)
        df = df[df[col] <= pd.Timestamp(cutoff)].reset_index(drop=True)

    return df
