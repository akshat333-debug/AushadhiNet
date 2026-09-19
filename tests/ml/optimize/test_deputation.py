"""DoD test for ml/optimize/deputation.py + referral.py (step 23)."""
from __future__ import annotations

import pandas as pd

from ml.optimize.constraints import SolverConfig
from ml.optimize.deputation import solve as deputation_solve
from ml.optimize.referral import solve as referral_solve


# --- deputation ---

def test_deputation_fills_gap_without_double_booking_staff():
    gaps = pd.DataFrame([{"facility_id": "F1", "role": "MO", "gap": 1}])
    available = pd.DataFrame([
        {"facility_id": "F2", "role": "MO", "staff_id_hash": "h1", "spare": True},
    ])
    drive = [[0, 10], [10, 0]]
    orders, reason = deputation_solve(gaps, available, drive, ["F1", "F2"], SolverConfig())
    assert reason is None
    assert len(orders) == 1
    assert orders[0].staff_id_hash == "h1"
    assert orders[0].to_facility_id == "F1"


def test_deputation_never_double_books_one_staff_member_to_two_gaps():
    gaps = pd.DataFrame([
        {"facility_id": "F1", "role": "MO", "gap": 1},
        {"facility_id": "F3", "role": "MO", "gap": 1},
    ])
    available = pd.DataFrame([{"facility_id": "F2", "role": "MO", "staff_id_hash": "h1", "spare": True}])
    drive = [[0, 10, 10], [10, 0, 10], [10, 10, 0]]
    orders, reason = deputation_solve(gaps, available, drive, ["F1", "F2", "F3"], SolverConfig())
    assert reason is None
    staff_used = [o.staff_id_hash for o in orders]
    assert len(staff_used) == len(set(staff_used))  # h1 assigned at most once
    assert len(orders) == 1


def test_deputation_respects_drive_time_cap():
    gaps = pd.DataFrame([{"facility_id": "F1", "role": "MO", "gap": 1}])
    available = pd.DataFrame([{"facility_id": "F2", "role": "MO", "staff_id_hash": "h1", "spare": True}])
    drive = [[0, 200], [200, 0]]
    orders, reason = deputation_solve(gaps, available, drive, ["F1", "F2"], SolverConfig(max_drive_minutes=120))
    assert orders == []
    assert reason is not None


def test_deputation_ignores_non_spare_staff():
    gaps = pd.DataFrame([{"facility_id": "F1", "role": "MO", "gap": 1}])
    available = pd.DataFrame([{"facility_id": "F2", "role": "MO", "staff_id_hash": "h1", "spare": False}])
    drive = [[0, 10], [10, 0]]
    orders, reason = deputation_solve(gaps, available, drive, ["F1", "F2"], SolverConfig())
    assert orders == []


# --- referral ---

def test_referral_sends_to_nearest_facility_with_capacity():
    pressure = pd.DataFrame([{"facility_id": "F1", "patients_to_refer": 2}])
    beds = pd.DataFrame([
        {"facility_id": "F2", "free_beds": 5},
        {"facility_id": "F3", "free_beds": 5},
    ])
    drive = [[0, 30, 10], [30, 0, 20], [10, 20, 0]]
    orders, reason = referral_solve(pressure, beds, drive, ["F1", "F2", "F3"], SolverConfig())
    assert reason is None
    assert orders[0].to_facility_id == "F3"  # nearer than F2


def test_referral_never_exceeds_bed_capacity():
    pressure = pd.DataFrame([{"facility_id": "F1", "patients_to_refer": 10}])
    beds = pd.DataFrame([{"facility_id": "F2", "free_beds": 3}])
    drive = [[0, 10], [10, 0]]
    orders, reason = referral_solve(pressure, beds, drive, ["F1", "F2"], SolverConfig())
    assert sum(o.patient_count for o in orders) <= 3


def test_referral_respects_drive_time_cap():
    pressure = pd.DataFrame([{"facility_id": "F1", "patients_to_refer": 2}])
    beds = pd.DataFrame([{"facility_id": "F2", "free_beds": 5}])
    drive = [[0, 200], [200, 0]]
    orders, reason = referral_solve(pressure, beds, drive, ["F1", "F2"], SolverConfig(max_drive_minutes=120))
    assert orders == []
    assert reason is not None
