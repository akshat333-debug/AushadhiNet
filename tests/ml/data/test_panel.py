"""DoD test for ml/data/panel.py (step 12)."""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from backend.domain import Grain
from ml.data.panel import REQUIRED_COLUMNS, build


def test_district_month_no_nan_in_required_columns():
    """Join keys must never be NaN. The HMIS measurement columns are
    exempt on purpose (data/README.md: ~12-15% of real district-month-drug
    combinations are genuinely unreported)."""
    panel = build(Grain.DISTRICT_MONTH, states=["mah"])
    for col in REQUIRED_COLUMNS[Grain.DISTRICT_MONTH]:
        assert panel[col].notna().all(), f"unexpected NaN in required column {col}"


def test_district_month_measurement_gaps_are_a_known_real_rate():
    """Document the real reporting gap rather than silently drop it: fails
    loudly if the gap rate moves outside the observed real-data range,
    which would signal a parsing regression rather than normal sparsity."""
    panel = build(Grain.DISTRICT_MONTH, states=["mah"])
    gap_rate = panel["distributed"].isna().mean()
    assert 0.05 < gap_rate < 0.30, f"distributed NaN rate {gap_rate:.2%} outside expected real-data range"


def test_facility_week_no_nan_in_required_columns():
    panel = build(Grain.FACILITY_WEEK)
    for col in REQUIRED_COLUMNS[Grain.FACILITY_WEEK]:
        assert panel[col].notna().all(), f"unexpected NaN in required column {col}"


def test_district_month_cutoff_excludes_later_rows():
    cutoff = date(2019, 2, 28)
    panel = build(Grain.DISTRICT_MONTH, states=["mah"], cutoff=cutoff)
    assert (panel["month"] <= pd.Timestamp(cutoff)).all()
    uncut = build(Grain.DISTRICT_MONTH, states=["mah"])
    assert len(panel) < len(uncut), "cutoff should actually remove rows, not be a no-op"


def test_facility_week_cutoff_excludes_later_rows():
    cutoff = date(2018, 6, 30)
    panel = build(Grain.FACILITY_WEEK, cutoff=cutoff)
    assert (panel["week"] <= pd.Timestamp(cutoff)).all()
    uncut = build(Grain.FACILITY_WEEK)
    assert len(panel) < len(uncut)


def test_unknown_grain_raises():
    with pytest.raises(ValueError):
        build("not-a-grain")
