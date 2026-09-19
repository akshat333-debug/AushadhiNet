"""Parses HMIS M10 (childhood diseases) and M11 (NVBDCP: malaria, dengue,
kala-azar, JE) indicator rows into a district x indicator x month panel
(modular-plan.md step 9). These replace the IDSP/IHIP weekly outbreak
bulletins named in project.md (data/README.md deviation #1): IDSP is PDF
bulletins with no reliable machine-readable feed, while M10/M11 are real,
structured disease counts already in the files this project downloaded.
"""
from __future__ import annotations

import pathlib

import pandas as pd

from ml.data.hmis_m19 import _DISTRICT_COL_RE, _FILENAME_RE, _STATE_NAME, _calendar_year, _MONTH_NUM
from backend.domain.ids import district_id

DEFAULT_HMIS_DIR = pathlib.Path(__file__).resolve().parents[2] / "data" / "raw" / "hmis"

_STATE_CODE = {"Maharashtra": "MH", "Haryana": "HR", "Assam": "AS", "Meghalaya": "ML"}


def _parse_one_file(path: pathlib.Path, indicator_prefixes: tuple[str, ...]) -> pd.DataFrame:
    match = _FILENAME_RE.search(path.name)
    if not match:
        raise ValueError(f"unrecognised HMIS filename: {path.name}")
    state_name = _STATE_NAME[match.group("st")]
    month = pd.Timestamp(
        year=_calendar_year(match.group("fy"), match.group("mon")),
        month=_MONTH_NUM[match.group("mon")], day=1,
    )

    raw = pd.read_csv(path, encoding="latin-1", low_memory=False)
    ind = raw["Indicator"].astype(str).str.strip()
    rows = raw[ind.str.startswith(indicator_prefixes)]

    district_cols = [c for c in raw.columns if _DISTRICT_COL_RE.match(c) and not c.startswith("District - _")]

    records = []
    for col in district_cols:
        district_name = _DISTRICT_COL_RE.match(col).group("district").strip()
        for _, row in rows.iterrows():
            value = pd.to_numeric(row[col], errors="coerce")
            records.append({
                "state_code": _STATE_CODE[state_name],
                "district_id": district_id(state_name, district_name),
                "indicator": str(row["Parameters"]).strip(),
                "month": month,
                "count": value,
            })
    return pd.DataFrame.from_records(records)


def load_disease_signals(
    hmis_dir: pathlib.Path | str = DEFAULT_HMIS_DIR,
    states: list[str] | None = None,
) -> pd.DataFrame:
    """Long panel of M10 (childhood disease) and M11 (NVBDCP) counts, one
    row per district x indicator x month."""
    hmis_dir = pathlib.Path(hmis_dir)
    frames = []
    for path in sorted(hmis_dir.glob("hmis-item-*-for-*.csv")):
        match = _FILENAME_RE.search(path.name)
        if not match:
            continue
        if states is not None and match.group("st") not in states:
            continue
        frames.append(_parse_one_file(path, ("M10", "M11")))
    if not frames:
        return pd.DataFrame(columns=["state_code", "district_id", "indicator", "month", "count"])
    return pd.concat(frames, ignore_index=True)
