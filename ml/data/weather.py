"""Loads NASA POWER daily weather (replaces IMD -- data/README.md) into a
tidy DataFrame (modular-plan.md step 9, extended at step 12 to cover the
held-out district too).
"""
from __future__ import annotations

import json
import pathlib

import pandas as pd

WEATHER_DIR = pathlib.Path(__file__).resolve().parents[2] / "data" / "raw" / "weather"

FILL_VALUE = -999.0

# One NASA POWER point per district we need weather for: the pilot
# (Nashik) and the held-out district (Dhule), per eval/protocol.lock.
# Other Maharashtra districts have no weather fetched -- panel.py imputes
# their weather features from the training-window mean rather than
# blocking on fetching all ~35 district centroids.
_DISTRICT_FILES = {
    "mh/nashik": WEATHER_DIR / "nashik_power_daily_2013_2020.json",
    "mh/dhule": WEATHER_DIR / "dhule_power_daily_2013_2020.json",
}


def _load_one(json_path: pathlib.Path, district_id: str) -> pd.DataFrame:
    data = json.loads(json_path.read_text())
    params = data["properties"]["parameter"]
    dates = sorted(params["PRECTOTCORR"].keys())
    rows = [{
        "date": pd.Timestamp(d),
        "district_id": district_id,
        "rainfall_mm": params["PRECTOTCORR"][d],
        "temp_c": params["T2M"][d],
        "temp_max_c": params["T2M_MAX"][d],
        "humidity_pct": params["RH2M"][d],
    } for d in dates]
    df = pd.DataFrame(rows)
    for col in ("rainfall_mm", "temp_c", "temp_max_c", "humidity_pct"):
        df.loc[df[col] == FILL_VALUE, col] = pd.NA
    return df


def load_weather(json_path: pathlib.Path | str | None = None, district_id: str = "mh/nashik") -> pd.DataFrame:
    """Single-district load (kept for backward compatibility with step 9's
    tests): returns one row per day for `district_id`."""
    path = pathlib.Path(json_path) if json_path is not None else _DISTRICT_FILES[district_id]
    return _load_one(path, district_id)
