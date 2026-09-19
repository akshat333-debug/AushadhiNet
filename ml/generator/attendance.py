"""Synthetic staff check-in / absence pattern (modular-plan.md §2.8). One
row per facility x week x role: sanctioned count and present count. Not
per-individual check-ins -- that level of detail belongs to
backend/ingest, which produces real CheckIn records; this is only the
aggregate signal used to test the staffing-gap forecaster.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from backend.domain import Facility, FacilityType, StaffRole

from ml.generator.params import GeneratorParams

_SANCTIONED = {
    FacilityType.SC: {StaffRole.ANM: 1},
    FacilityType.PHC: {StaffRole.MO: 1, StaffRole.ANM: 2, StaffRole.PHARMACIST: 1},
    FacilityType.CHC: {StaffRole.MO: 3, StaffRole.ANM: 4, StaffRole.PHARMACIST: 2, StaffRole.LAB: 1},
    FacilityType.SDH: {StaffRole.MO: 6, StaffRole.ANM: 8, StaffRole.PHARMACIST: 3, StaffRole.LAB: 2},
    FacilityType.DH: {StaffRole.MO: 15, StaffRole.ANM: 20, StaffRole.PHARMACIST: 5, StaffRole.LAB: 4},
}


def simulate_attendance(
    facilities: list[Facility],
    weeks: list[pd.Timestamp],
    params: GeneratorParams,
) -> pd.DataFrame:
    """Returns facility_id, week, role, sanctioned, present."""
    rng = np.random.default_rng(params.seed + 3)
    rows = []
    for facility in facilities:
        roles = _SANCTIONED[facility.facility_type]
        # remoter blocks (heuristic: sub-centres and PHCs) run a lower,
        # more variable base attendance rate -- observable via facility_type
        base_rate = 0.82 if facility.facility_type in (FacilityType.SC, FacilityType.PHC) else 0.9
        for role, sanctioned in roles.items():
            for week in weeks:
                rate = float(np.clip(rng.normal(base_rate, 0.08), 0.3, 1.0))
                present = int(round(sanctioned * rate))
                rows.append({
                    "facility_id": facility.facility_id, "week": week, "role": role.value,
                    "sanctioned": sanctioned, "present": present,
                })
    return pd.DataFrame(rows)
