"""DoD test for eval/run_backtest.py (step 15)."""
from __future__ import annotations

import pandas as pd
import pytest

from backend.domain import Grain
from eval.protocol import load_protocol
from eval.run_backtest import TestWindowAccessError, backtest_data


def _toy_panel():
    rows = []
    for month in pd.date_range("2017-04-01", "2020-02-01", freq="MS"):
        rows.append({"district_id": "mh/nashik", "month": month, "distributed": 100.0})
        rows.append({"district_id": "mh/dhule", "month": month, "distributed": 90.0})
    return pd.DataFrame(rows)


def test_refuses_to_return_test_split():
    panel = _toy_panel()
    with pytest.raises(TestWindowAccessError):
        backtest_data(panel, Grain.DISTRICT_MONTH, include=("test",))


def test_refuses_even_when_test_mixed_with_others():
    panel = _toy_panel()
    with pytest.raises(TestWindowAccessError):
        backtest_data(panel, Grain.DISTRICT_MONTH, include=("train", "test"))


def test_train_and_val_never_include_test_window_dates():
    protocol = load_protocol()
    panel = _toy_panel()
    result = backtest_data(panel, Grain.DISTRICT_MONTH, protocol=protocol)
    for split_name, df in result.items():
        assert (pd.to_datetime(df["month"]) < pd.Timestamp(protocol.real_benchmark.test_start)).all(), split_name


def test_train_and_val_exclude_held_out_district():
    protocol = load_protocol()
    panel = _toy_panel()
    result = backtest_data(panel, Grain.DISTRICT_MONTH, protocol=protocol)
    for df in result.values():
        assert "mh/dhule" not in set(df["district_id"])


def test_default_include_is_train_and_val_only():
    panel = _toy_panel()
    result = backtest_data(panel, Grain.DISTRICT_MONTH)
    assert set(result.keys()) == {"train", "val"}
