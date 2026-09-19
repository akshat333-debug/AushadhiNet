"""DoD test for ml/forecast/reconcile.py (step 20)."""
from __future__ import annotations

import pandas as pd
import pytest

from ml.forecast.reconcile import apply


def _hierarchy():
    return pd.DataFrame([
        {"facility_id": "F1", "block": "B1", "district_id": "mh/nashik"},
        {"facility_id": "F2", "block": "B1", "district_id": "mh/nashik"},
        {"facility_id": "F3", "block": "B2", "district_id": "mh/nashik"},
    ])


def _forecasts():
    return pd.DataFrame([
        {"facility_id": "F1", "drug_id": "ors", "p50": 10.0},
        {"facility_id": "F2", "drug_id": "ors", "p50": 20.0},
        {"facility_id": "F3", "drug_id": "ors", "p50": 5.0},
    ])


def test_facility_forecasts_sum_to_district_total():
    result = apply(_forecasts(), _hierarchy())
    district_row = result[(result.level == "district") & (result.entity_id == "mh/nashik") & (result.drug_id == "ors")]
    assert district_row["p50"].iloc[0] == pytest.approx(35.0)


def test_facility_forecasts_sum_to_block_total():
    result = apply(_forecasts(), _hierarchy())
    b1 = result[(result.level == "block") & (result.entity_id == "B1") & (result.drug_id == "ors")]
    assert b1["p50"].iloc[0] == pytest.approx(30.0)


def test_all_three_levels_present():
    result = apply(_forecasts(), _hierarchy())
    assert set(result["level"].unique()) == {"facility", "block", "district"}


def test_facility_level_preserves_original_values():
    result = apply(_forecasts(), _hierarchy())
    facility_rows = result[result.level == "facility"].set_index("entity_id")["p50"]
    assert facility_rows["F1"] == 10.0
    assert facility_rows["F2"] == 20.0
    assert facility_rows["F3"] == 5.0
