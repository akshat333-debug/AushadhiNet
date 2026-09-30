"""Public transparency view (modular-plan.md §5.5, project.md §4's public
role): aggregate district counts only, no facility-level identifiers --
what distinguishes this from a monitoring dashboard leak.
"""
from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter


router = APIRouter(prefix="/public", tags=["public"])


@router.get("/drug-names")
def drug_names() -> dict[str, dict[str, str]]:
    """Localized display names for every tracked medicine, keyed by drug id then language."""
    from backend.i18n import DRUG_NAMES
    return DRUG_NAMES


@router.get("/facility-points")
def facility_points(district_id: str = "mh/nashik") -> list[list[float]]:
    """[lat, lon] of each facility in a district: locations from the public government
    directory only, no ids, names or stock, so it reveals nothing the registry doesn't."""
    from ml.data.facilities import served_facility_index
    return [[f.lat, f.lon] for f in served_facility_index().values() if f.district_id == district_id]


@router.get("/district-summary")
def district_summary() -> list[dict]:
    """One row per district: facilities reporting, facilities with any drug
    under one week of cover (latest report per drug), and the same count per
    drug. Never emits a facility ID, name or address."""
    from backend.runtime import below_cover, latest_records
    from ml.data.facilities import served_facility_index as facility_index
    index = facility_index()

    latest = latest_records()

    reporting: dict[str, set] = defaultdict(set)
    at_risk: dict[str, set] = defaultdict(set)
    by_drug: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for (facility_id, drug_id), record in latest.items():
        facility = index.get(facility_id)
        if facility is None:
            continue
        reporting[facility.district_id].add(facility_id)
        if below_cover(record):
            at_risk[facility.district_id].add(facility_id)
            by_drug[facility.district_id][drug_id] += 1

    return [
        {"district_id": d, "facilities_reporting": len(f), "facilities_at_risk": len(at_risk[d]),
         "at_risk_by_drug": dict(sorted(by_drug[d].items(), key=lambda kv: -kv[1]))}
        for d, f in sorted(reporting.items())
    ]
