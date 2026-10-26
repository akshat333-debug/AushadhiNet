"""State codes stay unique across the whole national directory."""
from __future__ import annotations

from backend.domain.ids import STATE_CODES, district_id, facility_id


def test_states_that_share_a_prefix_get_different_ids():
    """Regression: two-letter guesses gave Uttar Pradesh and Uttarakhand the same "UT" prefix,
    so 1,939 facility IDs collided once both states were loaded."""
    assert facility_id("Uttar Pradesh", 1) != facility_id("Uttarakhand", 1)
    assert district_id("Madhya Pradesh", "x") != district_id("Manipur", "x")


def test_every_directory_state_has_a_code():
    import pandas as pd
    from ml.data.facilities import DEFAULT_CSV
    names = pd.read_csv(DEFAULT_CSV, usecols=["State Name"])["State Name"].astype(str).str.strip().str.lower().unique()
    assert set(names) <= set(STATE_CODES)
