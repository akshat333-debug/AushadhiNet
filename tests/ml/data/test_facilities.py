"""DoD test for ml/data/facilities.py (step 6)."""
from __future__ import annotations

from ml.data.facilities import load_facilities


def test_nashik_facility_count_and_coordinates():
    facilities = load_facilities(state="Maharashtra", district="Nashik")
    assert len(facilities) == 760
    assert all(-90 <= f.lat <= 90 and -180 <= f.lon <= 180 for f in facilities)
    assert all(f.district_id == "mh/nashik" for f in facilities)


def test_facility_ids_are_unique():
    facilities = load_facilities(state="Maharashtra", district="Nashik")
    ids = [f.facility_id for f in facilities]
    assert len(ids) == len(set(ids))


def test_federation_states_all_load():
    for state in ("Maharashtra", "Haryana", "Assam", "Meghalaya"):
        facilities = load_facilities(state=state)
        assert len(facilities) > 0, f"no facilities loaded for {state}"
