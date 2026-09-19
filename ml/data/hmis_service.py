"""Parses HMIS service-delivery indicators used as demand proxies
(project.md §10): OPD footfall, deliveries, and an inpatient-headcount
series used as the bed-occupancy proxy (modular-plan.md step 9).
"""
from __future__ import annotations

import pathlib

import pandas as pd

from ml.data.hmis_m19 import _DISTRICT_COL_RE, _FILENAME_RE, _STATE_NAME, _calendar_year, _MONTH_NUM
from backend.domain.ids import district_id

DEFAULT_HMIS_DIR = pathlib.Path(__file__).resolve().parents[2] / "data" / "raw" / "hmis"

_STATE_CODE = {"Maharashtra": "MH", "Haryana": "HR", "Assam": "AS", "Meghalaya": "ML"}

# Exact "Parameters" strings used as service-delivery demand proxies.
SERVICE_INDICATORS = {
    "opd_attendance": "Allopathic- Outpatient attendance",
    "inpatient_midnight_census": "In-Patient Head Count at midnight",
    "institutional_deliveries": "Number of Institutional Deliveries conducted (Including C-Sections)",
}


def _parse_one_file(path: pathlib.Path) -> pd.DataFrame:
    match = _FILENAME_RE.search(path.name)
    if not match:
        raise ValueError(f"unrecognised HMIS filename: {path.name}")
    state_name = _STATE_NAME[match.group("st")]
    month = pd.Timestamp(
        year=_calendar_year(match.group("fy"), match.group("mon")),
        month=_MONTH_NUM[match.group("mon")], day=1,
    )

    raw = pd.read_csv(path, encoding="latin-1", low_memory=False)
    params = raw["Parameters"].astype(str).str.strip()
    wanted = set(SERVICE_INDICATORS.values())
    rows = raw[params.isin(wanted)]

    district_cols = [c for c in raw.columns if _DISTRICT_COL_RE.match(c) and not c.startswith("District - _")]
    name_to_key = {v: k for k, v in SERVICE_INDICATORS.items()}

    records = []
    for col in district_cols:
        district_name = _DISTRICT_COL_RE.match(col).group("district").strip()
        values: dict[str, float] = {}
        for _, row in rows.iterrows():
            key = name_to_key[str(row["Parameters"]).strip()]
            values[key] = pd.to_numeric(row[col], errors="coerce")
        record = {
            "state_code": _STATE_CODE[state_name],
            "district_id": district_id(state_name, district_name),
            "month": month,
        }
        record.update({k: values.get(k) for k in SERVICE_INDICATORS})
        records.append(record)
    return pd.DataFrame.from_records(records)


def load_service_indicators(
    hmis_dir: pathlib.Path | str = DEFAULT_HMIS_DIR,
    states: list[str] | None = None,
) -> pd.DataFrame:
    hmis_dir = pathlib.Path(hmis_dir)
    frames = []
    for path in sorted(hmis_dir.glob("hmis-item-*-for-*.csv")):
        match = _FILENAME_RE.search(path.name)
        if not match:
            continue
        if states is not None and match.group("st") not in states:
            continue
        frames.append(_parse_one_file(path))
    if not frames:
        return pd.DataFrame(columns=["state_code", "district_id", "month", *SERVICE_INDICATORS])
    return pd.concat(frames, ignore_index=True)
