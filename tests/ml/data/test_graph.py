"""DoD test for ml/data/graph.py (step 12)."""
from __future__ import annotations

import numpy as np

from backend.domain import Facility, FacilityType
from ml.data.graph import CACHE_DIR, HaversineProvider, drive_matrix


def _facs():
    return [
        Facility(facility_id="MH-0000001", name="A", state_code="MH", district_id="mh/nashik",
                  facility_type=FacilityType.PHC, lat=20.0, lon=73.8),
        Facility(facility_id="MH-0000002", name="B", state_code="MH", district_id="mh/nashik",
                  facility_type=FacilityType.PHC, lat=20.1, lon=73.9),
        Facility(facility_id="MH-0000003", name="C", state_code="MH", district_id="mh/nashik",
                  facility_type=FacilityType.CHC, lat=20.2, lon=74.0),
    ]


def test_matrix_symmetric_and_no_self_edges(tmp_path):
    facs = _facs()
    m = drive_matrix(facs, provider=HaversineProvider(), cache_dir=tmp_path)
    assert np.allclose(m, m.T)
    assert np.allclose(np.diag(m), 0.0)
    assert (m[~np.eye(len(facs), dtype=bool)] > 0).all()


def test_cache_hit_avoids_recompute(tmp_path):
    facs = _facs()
    calls = {"n": 0}

    class CountingProvider(HaversineProvider):
        def drive_minutes(self, a, b):
            calls["n"] += 1
            return super().drive_minutes(a, b)

    provider = CountingProvider()
    m1 = drive_matrix(facs, provider=provider, cache_dir=tmp_path)
    first_calls = calls["n"]
    assert first_calls > 0

    m2 = drive_matrix(facs, provider=provider, cache_dir=tmp_path)
    assert calls["n"] == first_calls, "second call should hit the cache, not the provider"
    assert np.array_equal(m1, m2)


def test_use_cache_false_bypasses_cache(tmp_path):
    facs = _facs()
    drive_matrix(facs, provider=HaversineProvider(), cache_dir=tmp_path)  # warm cache
    calls = {"n": 0}

    class CountingProvider(HaversineProvider):
        def drive_minutes(self, a, b):
            calls["n"] += 1
            return super().drive_minutes(a, b)

    drive_matrix(facs, provider=CountingProvider(), cache_dir=tmp_path, use_cache=False)
    assert calls["n"] > 0
