"""Drive-time matrix between facilities (modular-plan.md §2.9, step 12).

`provider` is any object with a `drive_minutes(a: LatLon, b: LatLon) ->
float` method -- this is a structural match to the RouteProvider protocol
that backend/providers/ will define later (step 25); graph.py does not
import backend.providers to avoid a forward dependency, since ml/data/
must be usable standalone. `HaversineProvider` is the local/default
implementation (great-circle distance / an assumed rural average speed),
used until a real Maps Distance Matrix / Routes API provider is wired in.
"""
from __future__ import annotations

import hashlib
import math
import pathlib
from typing import Protocol

import numpy as np

from backend.domain import Facility

CACHE_DIR = pathlib.Path(__file__).resolve().parents[2] / "data" / "interim" / "drive_matrix_cache"


class LatLon(Protocol):
    lat: float
    lon: float


class DriveTimeProvider(Protocol):
    def drive_minutes(self, a: LatLon, b: LatLon) -> float: ...


class HaversineProvider:
    """Great-circle distance converted to minutes at an assumed average
    rural road speed. Not a real routing engine -- a placeholder until a
    Maps-backed provider exists, deliberately conservative (slow assumed
    speed) since PHC-network roads are rarely highway-grade."""

    def __init__(self, avg_speed_kmh: float = 30.0):
        self.avg_speed_kmh = avg_speed_kmh

    def drive_minutes(self, a: LatLon, b: LatLon) -> float:
        r_km = 6371.0
        lat1, lon1, lat2, lon2 = map(math.radians, (a.lat, a.lon, b.lat, b.lon))
        dlat, dlon = lat2 - lat1, lon2 - lon1
        h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        km = 2 * r_km * math.asin(math.sqrt(h))
        return (km / self.avg_speed_kmh) * 60.0


def _cache_key(facilities: list[Facility], provider: DriveTimeProvider) -> str:
    ids = ",".join(sorted(f.facility_id for f in facilities))
    provider_tag = f"{type(provider).__name__}:{getattr(provider, 'avg_speed_kmh', '')}"
    return hashlib.sha256(f"{ids}|{provider_tag}".encode()).hexdigest()[:24]


def drive_matrix(
    facilities: list[Facility],
    provider: DriveTimeProvider | None = None,
    cache_dir: pathlib.Path = CACHE_DIR,
    use_cache: bool = True,
) -> np.ndarray:
    """Symmetric NxN matrix of drive minutes, in the given facility order.
    Diagonal is 0. Cached to disk by (facility set, provider) since a full
    Maps API matrix is call-metered and expensive to recompute."""
    provider = provider or HaversineProvider()
    key = _cache_key(facilities, provider)
    cache_path = cache_dir / f"{key}.npy"

    if use_cache and cache_path.exists():
        return np.load(cache_path)

    n = len(facilities)
    matrix = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(i + 1, n):
            minutes = provider.drive_minutes(facilities[i], facilities[j])
            matrix[i, j] = minutes
            matrix[j, i] = minutes

    if use_cache:
        cache_dir.mkdir(parents=True, exist_ok=True)
        np.save(cache_path, matrix)
    return matrix
