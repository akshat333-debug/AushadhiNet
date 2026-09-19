"""DoD test for ml/optimize/transfers.py (step 22, AC6)."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from ml.optimize.constraints import SolverConfig
from ml.optimize.transfers import solve


def _batches(*items):
    return [{"batch_no": b, "qty": q, "expiry": datetime(*e, tzinfo=timezone.utc)} for b, q, e in items]


def test_known_optimum_3_facility_instance():
    """F1 has surplus of 50, F2 has surplus of 30 (both drive-feasible to
    F3's deficit of 40). F1 is closer (10min) than F2 (20min), so the
    known optimum sends all 40 units from F1 (cheaper)."""
    surplus = pd.DataFrame([
        {"facility_id": "F1", "drug_id": "ors", "on_hand": 50, "drug_cold_chain": False,
         "has_cold_chain": False, "batches": _batches(("B1", 50, (2020, 6, 1)))},
        {"facility_id": "F2", "drug_id": "ors", "on_hand": 30, "drug_cold_chain": False,
         "has_cold_chain": False, "batches": _batches(("B2", 30, (2020, 6, 1)))},
    ])
    deficit = pd.DataFrame([
        {"facility_id": "F3", "drug_id": "ors", "needed_qty": 40, "drug_cold_chain": False, "has_cold_chain": False},
    ])
    drive = [
        [0, 50, 10],
        [50, 0, 20],
        [10, 20, 0],
    ]
    orders, reason = solve(surplus, deficit, drive, ["F1", "F2", "F3"], SolverConfig())
    assert reason is None
    assert len(orders) == 1
    assert orders[0].from_facility_id == "F1"
    assert orders[0].to_facility_id == "F3"
    assert orders[0].quantity == 40


def test_buffer_floor_respected_at_source():
    surplus = pd.DataFrame([
        {"facility_id": "F1", "drug_id": "ors", "on_hand": 50, "drug_cold_chain": False,
         "has_cold_chain": False, "batches": _batches(("B1", 50, (2020, 6, 1)))},
    ])
    deficit = pd.DataFrame([
        {"facility_id": "F2", "drug_id": "ors", "needed_qty": 100, "drug_cold_chain": False, "has_cold_chain": False},
    ])
    drive = [[0, 10], [10, 0]]
    cfg = SolverConfig(buffer_floor=20)
    orders, reason = solve(surplus, deficit, drive, ["F1", "F2"], cfg)
    assert reason is None
    assert orders[0].quantity <= 30  # 50 - buffer_floor(20)


def test_drive_time_cap_excludes_far_facility():
    surplus = pd.DataFrame([
        {"facility_id": "F1", "drug_id": "ors", "on_hand": 50, "drug_cold_chain": False,
         "has_cold_chain": False, "batches": _batches(("B1", 50, (2020, 6, 1)))},
    ])
    deficit = pd.DataFrame([
        {"facility_id": "F2", "drug_id": "ors", "needed_qty": 20, "drug_cold_chain": False, "has_cold_chain": False},
    ])
    drive = [[0, 200], [200, 0]]  # 200 min > default cap
    orders, reason = solve(surplus, deficit, drive, ["F1", "F2"], SolverConfig(max_drive_minutes=120))
    assert orders == []
    assert reason is not None


def test_cold_chain_drug_blocked_without_capability_at_destination():
    surplus = pd.DataFrame([
        {"facility_id": "F1", "drug_id": "vaccine", "on_hand": 50, "drug_cold_chain": True,
         "has_cold_chain": True, "batches": _batches(("B1", 50, (2020, 6, 1)))},
    ])
    deficit = pd.DataFrame([
        {"facility_id": "F2", "drug_id": "vaccine", "needed_qty": 20, "drug_cold_chain": True, "has_cold_chain": False},
    ])
    drive = [[0, 10], [10, 0]]
    orders, reason = solve(surplus, deficit, drive, ["F1", "F2"], SolverConfig())
    assert orders == []
    assert "cold" in reason.lower()


def test_fefo_picks_earliest_expiring_batch_first():
    surplus = pd.DataFrame([
        {"facility_id": "F1", "drug_id": "ors", "on_hand": 30, "drug_cold_chain": False, "has_cold_chain": False,
         "batches": _batches(("OLD", 10, (2020, 1, 1)), ("NEW", 20, (2021, 1, 1)))},
    ])
    deficit = pd.DataFrame([
        {"facility_id": "F2", "drug_id": "ors", "needed_qty": 15, "drug_cold_chain": False, "has_cold_chain": False},
    ])
    drive = [[0, 10], [10, 0]]
    orders, reason = solve(surplus, deficit, drive, ["F1", "F2"], SolverConfig())
    assert reason is None
    batch_nos = [b.batch_no for b in orders[0].batches]
    assert batch_nos[0] == "OLD"  # earliest-expiring consumed first
    assert sum(b.quantity for b in orders[0].batches) == 15


def test_infeasible_instance_returns_empty_list_and_reason_never_partial_illegal_plan():
    surplus = pd.DataFrame(columns=["facility_id", "drug_id", "on_hand", "drug_cold_chain", "has_cold_chain", "batches"])
    deficit = pd.DataFrame([{"facility_id": "F2", "drug_id": "ors", "needed_qty": 20, "drug_cold_chain": False, "has_cold_chain": False}])
    orders, reason = solve(surplus, deficit, [[0]], ["F2"], SolverConfig())
    assert orders == []
    assert reason is not None
