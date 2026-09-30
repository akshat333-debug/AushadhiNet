"""Loads the All India Health Centres Directory into Facility domain models
(modular-plan.md step 6). Read-only over data/raw/facilities/; never reads
os.environ (architecture.md §2) -- callers pass the CSV path explicitly.
"""
from __future__ import annotations

import pathlib
from functools import lru_cache

import pandas as pd

from backend.domain import Facility, FacilityType
from backend.domain.ids import district_id, facility_id

DEFAULT_CSV = (
    pathlib.Path(__file__).resolve().parents[2]
    / "data" / "raw" / "facilities" / "geocode_health_centre.csv"
)

_TYPE_MAP = {
    "sub_cen": FacilityType.SC,
    "phc": FacilityType.PHC,
    "chc": FacilityType.CHC,
    "s_t_h": FacilityType.SDH,
    "dis_h": FacilityType.DH,
}

_STATE_CODE = {"maharashtra": "MH", "haryana": "HR", "assam": "AS", "meghalaya": "ML"}


def load_facilities(
    csv_path: pathlib.Path | str = DEFAULT_CSV,
    state: str | None = None,
    district: str | None = None,
) -> list[Facility]:
    """Parse the facility directory, optionally filtered to one state
    and/or one district (case-insensitive).

    facility_id is assigned by each row's position within its STATE
    subset (never further filtered by district first) specifically so
    that the same real-world facility gets the same facility_id whether
    it is loaded via load_facilities(district="Nashik") or via a broader
    call that includes Nashik incidentally (e.g. no filter at all) --
    two calls that return different ID numbering for what is supposed to
    be a stable identifier is a real cross-call consistency bug, not
    just a cosmetic one (a record seeded under one call's ID would never
    be found by code that looks it up via another call's numbering).
    District filtering is applied only to what is RETURNED, after IDs are
    assigned, so it never perturbs the numbering.

    Rows with an unmapped facility type or missing/invalid coordinates
    are skipped rather than raising, since the source directory has a
    handful of malformed rows nationally (misaligned columns, sentinel
    coordinates)."""
    # Only the columns used below, so a national load stays small enough for a 512 MB instance.
    columns = ["State Name", "District Name", "Subdistrict Name", "Facility Name", "Facility Type", "Latitude", "Longitude"]
    # Chunked so a national read never holds the whole directory in memory at once.
    chunks = []
    wanted_state = state.strip().lower() if state is not None else None
    for chunk in pd.read_csv(csv_path, usecols=columns, chunksize=25_000, low_memory=False):
        if wanted_state is not None:
            chunk = chunk[chunk["State Name"].str.strip().str.lower() == wanted_state]
        if not chunk.empty:
            chunks.append(chunk)
    df = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame(columns=columns)

    df = df.rename(columns={
        "State Name": "state_name", "District Name": "district_name", "Subdistrict Name": "block",
        "Facility Name": "name", "Facility Type": "ftype",
    })
    df["lat_num"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["lon_num"] = pd.to_numeric(df["Longitude"], errors="coerce")

    facilities: list[Facility] = []
    counters: dict[str, int] = {}
    wanted_district = district.strip().lower() if district is not None else None
    for row in df.itertuples(index=False):
        ftype = _TYPE_MAP.get(str(row.ftype).strip().lower())
        lat, lon = row.lat_num, row.lon_num
        if ftype is None or pd.isna(lat) or pd.isna(lon):
            continue
        lat, lon = float(lat), float(lon)
        if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
            continue  # a handful of source rows carry sentinel/garbage coordinates

        state_name = str(row.state_name).strip()
        state_code = _STATE_CODE.get(state_name.lower(), state_name[:2].upper())
        counters[state_code] = counters.get(state_code, 0) + 1
        fac_id = facility_id(state_name, counters[state_code])

        row_district = str(row.district_name).strip()
        if wanted_district is not None and row_district.lower() != wanted_district:
            continue  # ID already assigned above; only the return set is filtered

        block = row.block
        facilities.append(
            Facility(
                facility_id=fac_id,
                name=str(row.name),
                state_code=state_code,
                district_id=district_id(state_name, row_district),
                block=(None if pd.isna(block) else str(block)),
                facility_type=ftype,
                lat=lat,
                lon=lon,
            )
        )
    return facilities


@lru_cache(maxsize=1)
def facility_index(states: tuple[str, ...] | None = None) -> dict[str, Facility]:
    """Facilities keyed by facility_id, for the given states (default: all).

    The API passes only the states it serves: the national directory is 200k
    facilities and ~480 MB of model objects, which does not fit a small instance.
    IDs are assigned per state, so filtering by state never changes them."""
    if states is None:
        return {f.facility_id: f for f in load_facilities()}
    index: dict[str, Facility] = {}
    for state in states:
        index.update({f.facility_id: f for f in load_facilities(state=state)})
    return index


def served_facility_index() -> dict[str, Facility]:
    """The API's view of the directory (backend.config.served_states)."""
    from backend.config import get_settings
    return facility_index(tuple(get_settings().served_states_list))
