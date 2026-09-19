"""Base demand shape: the observable part of synthetic demand (modular-
plan.md §2.8). Deterministic given the seed; a real forecaster trained on
real observable features (facility type, calendar month) could in
principle recover this shape -- that is by design, it is not the hidden
part the isolation rule is protecting.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from backend.domain import Drug, Facility

from ml.generator.params import GeneratorParams

# Drugs whose real-world demand rises in the monsoon (data/README.md:
# rainfall/humidity-linked disease burden). Matched by substring on name.
_MONSOON_SENSITIVE_SUBSTRINGS = ("ors", "zinc", "albendazole")


def _is_monsoon_sensitive(drug: Drug) -> bool:
    name = drug.name.lower()
    return any(s in name for s in _MONSOON_SENSITIVE_SUBSTRINGS)


def _facility_baseline(facilities: list[Facility], params: GeneratorParams, rng: np.random.Generator) -> dict[str, float]:
    """Per-facility multiplicative heterogeneity (some PHCs just see more
    patients than others of the same type), lognormal around 1.0."""
    return {
        f.facility_id: float(rng.lognormal(mean=0.0, sigma=params.facility_heterogeneity_sigma))
        for f in facilities
    }


def base_shape(
    facilities: list[Facility],
    drugs: list[Drug],
    weeks: list[pd.Timestamp],
    params: GeneratorParams,
) -> pd.DataFrame:
    """Returns facility_id, drug_id, week, base_intensity (unit-mean, i.e.
    averaging base_intensity over facilities of the same type and over
    non-monsoon weeks gives approximately 1.0). anchor.py rescales this to
    match real district-month totals; ledger.py turns it into an actual
    inventory simulation."""
    rng = np.random.default_rng(params.seed)
    heterogeneity = _facility_baseline(facilities, params, rng)
    monsoon_flags = {d.drug_id: _is_monsoon_sensitive(d) for d in drugs}

    rows = []
    for facility in facilities:
        ftype_weight = params.facility_type_weight[facility.facility_type]
        het = heterogeneity[facility.facility_id]
        for drug in drugs:
            monsoon = monsoon_flags[drug.drug_id]
            for week in weeks:
                seasonal = params.monsoon_multiplier if (monsoon and week.month in params.monsoon_months) else 1.0
                rows.append((facility.facility_id, drug.drug_id, week, ftype_weight * het * seasonal))
    return pd.DataFrame(rows, columns=["facility_id", "drug_id", "week", "base_intensity"])
