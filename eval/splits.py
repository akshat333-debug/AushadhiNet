"""Turns the frozen protocol into concrete train/val/test row filters
(modular-plan.md §2.10). This is the one place a caller gets "the split"
from -- eval/run_backtest.py and eval/run_final.py both go through here
rather than re-deriving date arithmetic themselves.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

from backend.domain import Grain

from eval.protocol import Protocol


@dataclass(frozen=True)
class Split:
    train_start: date
    train_end: date
    val_start: date | None
    val_end: date | None
    test_start: date
    test_end: date
    held_out_entity: str  # district_id or block name, excluded from ALL splits
    date_column: str  # "month" or "week"

    def train_mask(self, df: pd.DataFrame) -> pd.Series:
        col = pd.to_datetime(df[self.date_column])
        entity_col = "district_id" if self.date_column == "month" else "block"
        in_window = (col >= pd.Timestamp(self.train_start)) & (col <= pd.Timestamp(self.train_end))
        if entity_col in df.columns:
            in_window &= df[entity_col] != self.held_out_entity
        return in_window

    def val_mask(self, df: pd.DataFrame) -> pd.Series:
        if self.val_start is None:
            return pd.Series(False, index=df.index)
        col = pd.to_datetime(df[self.date_column])
        entity_col = "district_id" if self.date_column == "month" else "block"
        in_window = (col >= pd.Timestamp(self.val_start)) & (col <= pd.Timestamp(self.val_end))
        if entity_col in df.columns:
            in_window &= df[entity_col] != self.held_out_entity
        return in_window

    def test_mask(self, df: pd.DataFrame) -> pd.Series:
        col = pd.to_datetime(df[self.date_column])
        return (col >= pd.Timestamp(self.test_start)) & (col <= pd.Timestamp(self.test_end))


def for_grain(grain: Grain, protocol: Protocol, panel_max_date: date | None = None) -> Split:
    """`panel_max_date` is required for FACILITY_WEEK: the synthetic
    benchmark's test window is "the trailing N weeks of whatever the
    ledger covers" (protocol.lock's synthetic_benchmark.test_weeks),
    expressed relative to the panel in hand rather than an absolute date,
    since the synthetic calendar has no independent meaning of its own."""
    if grain == Grain.DISTRICT_MONTH:
        rb = protocol.real_benchmark
        return Split(
            train_start=rb.train_start, train_end=rb.train_end,
            val_start=rb.validation_start, val_end=rb.validation_end,
            test_start=rb.test_start, test_end=rb.test_end,
            held_out_entity=f"{rb.held_out_district_state}/{rb.held_out_district}", date_column="month",
        )
    if grain == Grain.FACILITY_WEEK:
        if panel_max_date is None:
            raise ValueError("panel_max_date is required to compute the FACILITY_WEEK split")
        sb = protocol.synthetic_benchmark
        test_end = panel_max_date
        test_start = test_end - timedelta(weeks=sb.test_weeks - 1)
        train_end = test_start - timedelta(weeks=1)
        return Split(
            train_start=date.min, train_end=train_end,
            val_start=None, val_end=None,
            test_start=test_start, test_end=test_end,
            held_out_entity=sb.held_out_block, date_column="week",
        )
    raise ValueError(f"unknown grain: {grain}")
