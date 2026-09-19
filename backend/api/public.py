"""Public transparency view (modular-plan.md §5.5, project.md §4's public
role): aggregate district stock-out days only, no facility-level
identifiers -- what distinguishes this from a monitoring dashboard leak.
"""
from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter

from backend.domain import RecordStatus
from backend.providers import factory

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/district-summary")
def district_summary() -> list[dict]:
    """Returns one row per district: stock-out-risk facility count
    (aggregated), never a facility ID, name, or address."""
    live = factory.get("store_live")
    records = live.query("stock_records", {"status": RecordStatus.CONFIRMED})

    # facility_id -> district_id would normally come from the facility
    # directory; this endpoint only ever emits the district_id, never
    # the facility_id it was derived from.
    from ml.data.facilities import load_facilities
    facility_district = {f.facility_id: f.district_id for f in load_facilities()}

    at_risk_by_district: dict[str, int] = defaultdict(int)
    total_by_district: dict[str, int] = defaultdict(int)
    LOW_STOCK_THRESHOLD = 5

    for record in records:
        district_id = facility_district.get(record.facility_id)
        if district_id is None:
            continue
        total_by_district[district_id] += 1
        if record.on_hand <= LOW_STOCK_THRESHOLD:
            at_risk_by_district[district_id] += 1

    return [
        {"district_id": district_id, "facilities_reporting": total, "facilities_at_risk": at_risk_by_district.get(district_id, 0)}
        for district_id, total in sorted(total_by_district.items())
    ]
