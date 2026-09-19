"""Sealed synthetic ledger generator (modular-plan.md §2.8).

Nothing outside ml/generator/ and eval/ may import this package
(architecture.md §5, enforced by tests/test_isolation.py) -- the sealed
generator must never be readable by the code that is scored against it.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from backend.domain import Drug, Facility

from ml.generator.anchor import scale_to_anchor
from ml.generator.attendance import simulate_attendance
from ml.generator.beds import simulate_beds
from ml.generator.demand import base_shape
from ml.generator.ledger import simulate_ledger
from ml.generator.params import GeneratorParams


@dataclass
class LedgerBundle:
    stock: pd.DataFrame
    beds: pd.DataFrame
    attendance: pd.DataFrame


def _iso_weeks(start: date, end: date) -> list[pd.Timestamp]:
    """Monday-anchored weeks from start to end, inclusive of the week
    containing `end`."""
    first_monday = pd.Timestamp(start) - pd.Timedelta(days=pd.Timestamp(start).weekday())
    last_monday = pd.Timestamp(end) - pd.Timedelta(days=pd.Timestamp(end).weekday())
    return list(pd.date_range(first_monday, last_monday, freq="W-MON"))


def generate(
    seed: int,
    facilities: list[Facility],
    drugs: list[Drug],
    start: date,
    end: date,
    anchors: pd.DataFrame | None = None,
    params: GeneratorParams | None = None,
) -> LedgerBundle:
    """The one entry point (modular-plan.md §2.8). `anchors`, if given, must
    already carry columns [district_id, drug_id, month, distributed]
    (cli.py resolves HMIS drug_name -> drug_id before calling this)."""
    params = params or GeneratorParams(seed=seed)
    weeks = _iso_weeks(start, end)

    shape = base_shape(facilities, drugs, weeks, params)
    facility_district = {f.facility_id: f.district_id for f in facilities}
    targets = scale_to_anchor(shape, facility_district, anchors)

    stock = simulate_ledger(targets[["facility_id", "drug_id", "week", "target_dispense"]], weeks, params)
    beds = simulate_beds(facilities, weeks, params)
    attendance = simulate_attendance(facilities, weeks, params)

    return LedgerBundle(stock=stock, beds=beds, attendance=attendance)
