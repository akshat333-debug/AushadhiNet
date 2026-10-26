"""Beds and staff: the brief's other two resources besides medicines. Nurses report beds on
WhatsApp as 'BEDS 4/6' and check in by sharing their location (backend/runtime.handle_inbound);
`district_capacity` turns the day's reports into what an officer acts on: facilities nearly
full, with referral suggestions, and staff gaps, with deputation suggestions, both from the
OR-Tools solvers in ml/optimize.

In local and demo mode a generated baseline for the day stands in for the facilities that
have not reported, and a live WhatsApp report replaces it. The baseline is never stored.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from datetime import date, datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from backend.domain import FacilityType, StaffRole
from backend.providers import factory

IST = ZoneInfo("Asia/Kolkata")
FULL = 0.9    # occupancy at which a facility is flagged and referrals are suggested
TARGET = 0.8  # referrals bring a full facility down to this; receiving facilities fill up to it
SHOW = 10     # rows per list in the officer's summary
FRESH_DAYS = 1  # a bed census older than this is unknown, not current capacity

# "BEDS 4/6", "beds 4 of 6", "बेड ४/६": occupied, then total. \d matches native digits too.
_BEDS_RE = re.compile(
    r"^\s*(?:beds?|बेड|खाटा?|খাট|படுக்கை|పడకలు|ಹಾಸಿಗೆ)\s*[:\-]?\s*(\d+)\s*(?:/|of|\s)\s*(\d+)\s*$", re.IGNORECASE)


def parse_beds(body: str) -> tuple[int, int] | None:
    """(occupied, total) from a beds message, or None if it is not one."""
    m = _BEDS_RE.match(body or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def role_from(body: str) -> StaffRole:
    """The role named in a check-in's caption ('MO', 'ANM', ...), else OTHER."""
    words = {w.lower() for w in re.findall(r"\w+", body or "")}
    return next((r for r in StaffRole if r.value.lower() in words), StaffRole.OTHER)


def today() -> date:
    return datetime.now(IST).date()


# shortcut: beds and posts per facility type (IPHS-style norms), since the facility directory has
# neither; a real deployment loads sanctioned beds and posts from the state's HR and HMIS records.
# Kept here, not imported from ml/generator: serving code must never import the generator
# (tests/test_isolation.py).
BEDS_BY_TYPE = {FacilityType.SC: 0, FacilityType.PHC: 6, FacilityType.CHC: 30, FacilityType.SDH: 50, FacilityType.DH: 100}
POSTS_BY_TYPE = {
    FacilityType.PHC: {StaffRole.MO: 1, StaffRole.ANM: 2, StaffRole.PHARMACIST: 1},
    FacilityType.CHC: {StaffRole.MO: 3, StaffRole.ANM: 4, StaffRole.PHARMACIST: 2, StaffRole.LAB: 1},
    FacilityType.SDH: {StaffRole.MO: 6, StaffRole.ANM: 8, StaffRole.PHARMACIST: 3, StaffRole.LAB: 2},
    FacilityType.DH: {StaffRole.MO: 15, StaffRole.ANM: 20, StaffRole.PHARMACIST: 5, StaffRole.LAB: 4},
}


def _beds(facility) -> int:
    return facility.beds_sanctioned or BEDS_BY_TYPE[facility.facility_type]


def _roster(facility) -> dict[StaffRole, int]:
    return POSTS_BY_TYPE.get(facility.facility_type, {})  # sub-centres: no beds, one ANM out in the field


@lru_cache(maxsize=4)
def _baseline(district_id: str, day: date) -> tuple[dict, list]:
    """Generated beds and check-ins for one day, the same all day (seeded by the date)."""
    from ml.data.facilities import served_facility_index
    rng = np.random.default_rng(int(day.strftime("%Y%m%d")))
    beds, checkins = {}, []
    for f in sorted((f for f in served_facility_index().values() if f.district_id == district_id), key=lambda f: f.facility_id):
        total = _beds(f)
        if not total:
            continue
        beds[f.facility_id] = (int(rng.binomial(total, rng.beta(6, 3))), total)
        for role, n in _roster(f).items():
            for i in range(n):
                if rng.random() < 0.85:
                    far = rng.random() < 0.02
                    checkins.append({"facility_id": f.facility_id, "role": role, "staff": f"{f.facility_id}-{role.value}-{i}",
                                     "distance_m": float(rng.uniform(800, 4000) if far else rng.uniform(0, 150))})
    return beds, checkins


def _live(day: date) -> tuple[dict, list]:
    """Beds and today's check-ins reported on WhatsApp. shortcut: reads both collections in
    full, fine while they hold only real reports (the baseline is never stored); filter by
    date in the query once a district reports daily."""
    live = factory.get("store_live")
    beds = {r.facility_id: (r.beds_occupied, r.beds_total) for r in sorted(live.query("bed_census", {}), key=lambda r: r.as_of_date)
            if (day - r.as_of_date).days <= FRESH_DAYS}
    # One person checking in twice is one person: their latest check-in today counts.
    latest = {c.staff_id_hash: c for c in sorted(live.query("checkins", {}), key=lambda c: c.at) if c.at.astimezone(IST).date() == day}
    checkins = [{"facility_id": c.facility_id, "role": c.role, "staff": c.staff_id_hash, "distance_m": c.distance_m} for c in latest.values()]
    return beds, checkins


def district_capacity(district_id: str) -> dict:
    from backend.config import get_settings
    from ml.data.facilities import served_facility_index
    from ml.data.graph import drive_matrix
    from ml.optimize import deputation, referral
    from ml.optimize.constraints import SolverConfig

    settings = get_settings()
    day = today()
    index = {fid: f for fid, f in served_facility_index().items() if f.district_id == district_id}
    demo = settings.mode == "local" or settings.demo_mode
    base_beds, base_checkins = _baseline(district_id, day) if demo else ({}, [])
    live_beds, live_checkins = _live(day)
    beds = {**base_beds, **{fid: v for fid, v in live_beds.items() if fid in index}}
    reported = {c["facility_id"] for c in live_checkins}  # a facility's own check-ins replace its generated ones
    checkins = [c for c in live_checkins if c["facility_id"] in index] + [c for c in base_checkins if c["facility_id"] not in reported]

    on_site = [c for c in checkins if c["distance_m"] <= settings.geofence_radius_m]
    present: dict[tuple[str, StaffRole], list[str]] = {}
    for c in on_site:
        present.setdefault((c["facility_id"], c["role"]), []).append(c["staff"])
    roster = {fid: _roster(f) for fid, f in index.items() if _roster(f)}

    involved = sorted(set(beds) | set(roster))
    facilities = [index[fid] for fid in involved]
    drive = drive_matrix(facilities).tolist() if facilities else []
    cfg = SolverConfig()
    name = lambda fid: index[fid].name

    full = sorted(((fid, o, t) for fid, (o, t) in beds.items() if t and o >= FULL * t), key=lambda x: -x[1] / x[2])
    pressure = pd.DataFrame([{"facility_id": fid, "patients_to_refer": o - math.floor(TARGET * t)} for fid, o, t in full])
    free = pd.DataFrame([{"facility_id": fid, "free_beds": math.floor(TARGET * t) - o}
                         for fid, (o, t) in beds.items() if o < math.floor(TARGET * t)])
    referrals, _ = referral.solve(pressure, free, drive, involved, cfg)

    # A role with nobody on site is a gap; staff above half their facility's posts for that role can be spared.
    gaps = pd.DataFrame([{"facility_id": fid, "role": role.value, "gap": n}
                         for fid, roles in roster.items() for role, n in roles.items() if not present.get((fid, role))],
                        columns=["facility_id", "role", "gap"])
    spare = pd.DataFrame([{"facility_id": fid, "role": role.value, "staff_id_hash": s, "spare": True}
                          for (fid, role), staff in present.items() if fid in roster
                          for s in staff[math.ceil(roster[fid].get(role, 0) / 2) or 1:]],
                         columns=["facility_id", "role", "staff_id_hash", "spare"])
    deputations, _ = deputation.solve(gaps, spare, drive, involved, cfg)
    role_of = dict(zip(spare["staff_id_hash"], spare["role"]))

    nobody = [fid for fid in roster if not any(c["facility_id"] == fid for c in on_site)]
    # Suggestions an officer already approved today carry their order, so the card shows them as done.
    from backend.domain import OrderKind, OrderStatus
    done = {(o.kind, o.from_facility_id, o.to_facility_id): o.order_id
            for status in (OrderStatus.APPROVED, OrderStatus.RECEIVED)
            for o in factory.get("store_live").query("orders", {"status": status})
            if o.kind in (OrderKind.REFERRAL, OrderKind.DEPUTATION) and o.approved_at and o.approved_at.astimezone(IST).date() == day}
    return {
        "date": day.isoformat(),
        "demo_baseline": demo,
        "beds": {
            "facilities": len(beds),
            "occupied": sum(o for o, _ in beds.values()),
            "total": sum(t for _, t in beds.values()),
            "full": [{"facility_id": fid, "name": name(fid), "occupied": o, "total": t} for fid, o, t in full[:SHOW]],
            "full_count": len(full),
            "referrals": [{"from_id": r.from_facility_id, "from_name": name(r.from_facility_id), "to_id": r.to_facility_id,
                           "to_name": name(r.to_facility_id), "patients": r.patient_count, "minutes": round(r.drive_minutes),
                           "order_id": done.get((OrderKind.REFERRAL, r.from_facility_id, r.to_facility_id))}
                          for r in referrals[:SHOW]],
        },
        "staff": {
            "rostered": sum(n for roles in roster.values() for n in roles.values()),
            "present": len(on_site),
            "facilities": len(roster),
            "nobody": [{"facility_id": fid, "name": name(fid)} for fid in nobody[:SHOW]],
            "nobody_count": len(nobody),
            "off_site": [{"facility_id": c["facility_id"], "name": name(c["facility_id"]), "role": c["role"].value,
                          "distance_m": round(c["distance_m"])} for c in checkins if c["distance_m"] > settings.geofence_radius_m][:SHOW],
            "deputations": [{"role": role, "staff": n, "from_id": src, "from_name": name(src), "to_id": dst, "to_name": name(dst), "minutes": round(m),
                             "order_id": done.get((OrderKind.DEPUTATION, src, dst))}
                            for (m, role, src, dst), n in sorted(Counter(
                                (d.drive_minutes, role_of.get(d.staff_id_hash, ""), d.from_facility_id, d.to_facility_id) for d in deputations).items())[:SHOW]],
        },
    }
