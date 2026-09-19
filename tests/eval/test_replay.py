"""eval/replay_sim.py mechanics on a small hand-made world (the full replay takes minutes)."""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from backend.domain import BatchLine, OrderKind, TransferOrder
from eval.replay_sim import World, compare, initial_state, run_weeks
from eval.run_replay import windows
from ml.generator.params import GeneratorParams


def _world() -> World:
    weeks = list(pd.date_range("2019-01-07", periods=20, freq="W-MON"))
    target = np.array([[10.0] * 20, [2.0] * 20])  # A uses 10/week, B uses 2/week
    target[0, 12:] = 40.0                          # A's demand jumps late on
    zeros = np.zeros_like(target)
    return World([("A", "ors"), ("B", "ors")], weeks, target, target.copy(), zeros, zeros.astype(bool), GeneratorParams(seed=1))


def _order(qty: int) -> TransferOrder:
    return TransferOrder(order_id="t", kind=OrderKind.DRUG_TRANSFER, from_facility_id="B", to_facility_id="A", drug_id="ors",
                         quantity=qty, batches=[BatchLine(batch_no="x", quantity=qty)], drive_minutes=30.0,
                         rationale="test", created_at=datetime.now(timezone.utc), created_by="solver")


def test_no_policy_arms_are_identical():
    w = _world()
    r = compare(w, 10, 20, lambda obs, on_hand: [])
    assert r["status_quo"]["unmet_units"] == r["solver"]["unmet_units"]
    assert r["solver"]["transfers"] == 0


def test_transfers_are_capped_by_source_stock_and_can_cut_unmet_demand():
    w = _world()
    r = compare(w, 12, 14, lambda obs, on_hand: [_order(5)])
    assert 0 < r["solver"]["units_moved"] <= 10.0  # never more than the source holds
    assert r["solver"]["unmet_units"] < r["status_quo"]["unmet_units"]


def test_policy_sees_only_reported_history_not_true_demand():
    w = _world()
    seen = {}

    def spy(obs, on_hand):
        seen["cols"] = set(obs.columns)
        return []
    state = initial_state(w)
    run_weeks(w, state, 0, 12, spy)
    assert seen["cols"] == {"facility_id", "drug_id", "week", "dispensed", "on_hand_close"}


def test_dev_window_ends_where_test_window_starts():
    win = windows(149, 26)
    assert win["dev"] == (97, 123) and win["test"] == (123, 149)
