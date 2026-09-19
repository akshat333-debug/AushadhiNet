"""Parses HMIS 'M19 [Other Items]' rows into a district x drug x month
stock panel (modular-plan.md step 7). This is the real drug-stock data
behind project.md's real-data forecasting benchmark: each row gives
opening balance, receipts, unusable stock, distributed (=consumption) and
closing total, per district per drug per month.

Files are latin-1 encoded and some S.No. values carry a stray leading or
trailing quote character; this parser does not rely on S.No. at all, since
the Indicator column ("M19 [Other Items]") and the Type label are a
cleaner, quote-free join key.
"""
from __future__ import annotations

import pathlib
import re

import pandas as pd

from backend.domain.ids import district_id

DEFAULT_HMIS_DIR = pathlib.Path(__file__).resolve().parents[2] / "data" / "raw" / "hmis"

_FILENAME_RE = re.compile(r"hmis-item-(?P<fy>\d{4}-\d{2})-mn-(?P<st>[a-z]+)-for-(?P<mon>[A-Za-z]{3})\.csv$")

_STATE_NAME = {"mah": "Maharashtra", "har": "Haryana", "as": "Assam", "meg": "Meghalaya"}

_MONTH_NUM = {
    m: i + 1 for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    )
}

_TYPE_LABEL_TO_COLUMN = {
    "1. Balance From Previous Month": "balance_prev",
    "2. Stocks Received": "received",
    "3. Unusable Stock": "unusable",
    "4. Stock Distributed": "distributed",
    "5. Total Stock": "total",
}

_DISTRICT_COL_RE = re.compile(r"^District - (?P<district>[^-]+) - Total \[\(A\+B\) or \(C\+D\)\]$")


def _calendar_year(fy: str, month_abbr: str) -> int:
    fy_start = int(fy[:4])
    return fy_start + 1 if month_abbr in ("Jan", "Feb", "Mar") else fy_start


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
    m19 = raw[raw["Indicator"].astype(str).str.strip() == "M19 [Other Items]"].copy()
    m19["Type"] = m19["Type"].astype(str).str.strip()

    district_cols = [c for c in raw.columns if _DISTRICT_COL_RE.match(c) and not c.startswith("District - _")]

    records = []
    for col in district_cols:
        district_name = _DISTRICT_COL_RE.match(col).group("district").strip()
        sub = m19[["Parameters", "Type", col]].rename(columns={col: "value"})
        sub["value"] = pd.to_numeric(sub["value"], errors="coerce")
        wide = sub.pivot_table(index="Parameters", columns="Type", values="value", aggfunc="first")
        wide = wide.rename(columns=_TYPE_LABEL_TO_COLUMN)
        for drug_name, row in wide.iterrows():
            records.append({
                "state_code": {"Maharashtra": "MH", "Haryana": "HR", "Assam": "AS", "Meghalaya": "ML"}[state_name],
                "district_id": district_id(state_name, district_name),
                "district_name": district_name,
                "drug_name": drug_name,
                "month": month,
                "balance_prev": row.get("balance_prev"),
                "received": row.get("received"),
                "unusable": row.get("unusable"),
                "distributed": row.get("distributed"),
                "total": row.get("total"),
            })
    return pd.DataFrame.from_records(records)


def load_m19(
    hmis_dir: pathlib.Path | str = DEFAULT_HMIS_DIR,
    states: list[str] | None = None,
) -> pd.DataFrame:
    """Load every HMIS M19 CSV into one long panel. `states` filters by the
    3-letter filename code (mah/har/as/meg); default loads all four."""
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
        return pd.DataFrame(columns=[
            "state_code", "district_id", "district_name", "drug_name", "month",
            "balance_prev", "received", "unusable", "distributed", "total",
        ])
    panel = pd.concat(frames, ignore_index=True)
    panel["balance_identity_ok"] = (
        (panel["balance_prev"].fillna(0) + panel["received"].fillna(0) - panel["unusable"].fillna(0)
         - panel["distributed"].fillna(0)).round(0) == panel["total"].fillna(0).round(0)
    )
    return panel
