"""DoD test for ml/data/hmis_m19.py (step 7)."""
from __future__ import annotations

import pandas as pd

from ml.data.hmis_m19 import load_m19


def test_five_figures_present_for_nashik_ors():
    panel = load_m19(states=["mah"])
    row = panel[(panel.district_name == "Nashik") & (panel.drug_name == "ORS (New WHO)")
                & (panel.month == pd.Timestamp(2019, 7, 1))]
    assert len(row) == 1
    r = row.iloc[0]
    assert r.balance_prev == 506309
    assert r.received == 320950
    assert r.unusable == 0
    assert r.distributed == 67344
    assert r.total == 759915


def test_balance_identity_holds_for_almost_all_rows():
    panel = load_m19(states=["mah"])
    assert len(panel) > 1000
    assert panel["balance_identity_ok"].mean() >= 0.95


def test_covers_fy2017_18_onward_only_when_present():
    panel = load_m19(states=["mah"])
    assert panel["month"].min() >= pd.Timestamp(2017, 4, 1)
    assert panel["month"].max() <= pd.Timestamp(2020, 3, 1)


def test_all_four_federation_states_load():
    panel = load_m19()
    assert set(panel["state_code"].unique()) == {"MH", "HR", "AS", "ML"}


def test_district_ids_are_slugged():
    panel = load_m19(states=["mah"])
    assert (panel[panel.district_name == "Nashik"]["district_id"] == "mh/nashik").all()
