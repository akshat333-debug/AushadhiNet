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
    drug. Shortages split two ways: `escalate` lists drugs whose district-wide
    stock is below the solver's planning cover (2 weeks of district demand), so
    no facility can spare any and transfers cannot help; only procurement can; `facilities_needing_transfer` counts facilities short
    of something else, which nearby surplus can cover. Never emits a facility ID,
    name or address."""
    from backend.runtime import below_cover, latest_records, weekly_demand
    from ml.data.facilities import served_facility_index as facility_index
    from ml.optimize.constraints import SolverConfig
    index = facility_index()
    try:
        demand = weekly_demand()
    except FileNotFoundError:
        demand = {}

    latest = latest_records()

    reporting: dict[str, set] = defaultdict(set)
    short: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))  # district -> facility -> drugs
    by_drug: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    stock_sum: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    demand_sum: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for (facility_id, drug_id), record in latest.items():
        facility = index.get(facility_id)
        if facility is None:
            continue
        d = facility.district_id
        reporting[d].add(facility_id)
        stock_sum[d][drug_id] += record.on_hand
        demand_sum[d][drug_id] += demand.get((facility_id, drug_id), 0.0)
        if below_cover(record):
            short[d][facility_id].add(drug_id)
            by_drug[d][drug_id] += 1

    def escalate(d: str) -> dict[str, float]:
        return {drug: round(stock_sum[d][drug] / need, 2) for drug, need in demand_sum[d].items()
                if drug in by_drug[d] and stock_sum[d][drug] < SolverConfig().cover_weeks * need}

    rows = []
    for d, f in sorted(reporting.items()):
        gaps = escalate(d)
        rows.append({
            "district_id": d, "facilities_reporting": len(f), "facilities_at_risk": len(short[d]),
            "at_risk_by_drug": dict(sorted(by_drug[d].items(), key=lambda kv: -kv[1])),
            "escalate": dict(sorted(gaps.items(), key=lambda kv: kv[1])),
            # units that bring the district back to the planning cover: what to request from the state
            "procurement_units": {drug: round(SolverConfig().cover_weeks * demand_sum[d][drug] - stock_sum[d][drug]) for drug in gaps},
            "facilities_needing_transfer": sum(1 for drugs in short[d].values() if drugs - gaps.keys()),
        })
    return rows


@router.get("/coverage")
def coverage_view() -> list[dict]:
    """Every state in the national facility directory (MoHFW, 2016) with its facility and
    district counts, and how many of its districts are live (reporting stock) today: the
    reach a rollout covers without new data collection. Counts only, no facility names."""
    from collections import Counter
    from backend.domain.ids import district_id
    from ml.data.facilities import coverage
    live = Counter(r["district_id"].split("/")[0] for r in district_summary() if r["facilities_reporting"])
    rows = []
    for c in coverage():
        code = district_id(c["state"], "x").split("/")[0]
        rows.append({**c, "code": code, "live_districts": live.get(code, 0)})
    return rows
