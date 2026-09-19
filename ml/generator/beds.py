"""Synthetic bed census: beds_total (assigned by facility type, since the
real facility directory has no bed-capacity field) and a simulated daily
occupancy (modular-plan.md §2.8).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from backend.domain import Facility, FacilityType

from ml.generator.params import GeneratorParams

# Sanctioned beds are not in the facility directory (data/README.md); these
# are reasonable, published-average defaults per facility type used only
# for the synthetic ledger, never asserted as real capacity.
_DEFAULT_BEDS = {
    FacilityType.SC: 0, FacilityType.PHC: 6, FacilityType.CHC: 30,
    FacilityType.SDH: 50, FacilityType.DH: 100,
}


def beds_total_for(facility: Facility) -> int:
    return facility.beds_sanctioned or _DEFAULT_BEDS[facility.facility_type]


def simulate_beds(
    facilities: list[Facility],
    weeks: list[pd.Timestamp],
    params: GeneratorParams,
) -> pd.DataFrame:
    """Returns facility_id, week, beds_total, beds_occupied, admissions,
    discharges. Facilities with zero sanctioned beds (sub-centres) are
    skipped -- there is nothing to census."""
    rng = np.random.default_rng(params.seed + 2)
    rows = []
    for facility in facilities:
        total = beds_total_for(facility)
        if total <= 0:
            continue
        base_occupancy_rate = 0.55 if facility.facility_type == FacilityType.PHC else 0.7
        occupied = int(round(total * base_occupancy_rate))
        for week in weeks:
            seasonal = 1.15 if week.month in (6, 7, 8, 9) else 1.0
            target = min(total, max(0, int(round(total * base_occupancy_rate * seasonal
                                                   * float(rng.lognormal(0, 0.15))))))
            admissions = max(0, target - occupied) + int(rng.poisson(max(total * 0.1, 0.1)))
            discharges = max(0, occupied + admissions - target)
            occupied = max(0, min(total, occupied + admissions - discharges))
            rows.append({
                "facility_id": facility.facility_id, "week": week,
                "beds_total": total, "beds_occupied": occupied,
                "admissions": admissions, "discharges": discharges,
            })
    return pd.DataFrame(rows)
