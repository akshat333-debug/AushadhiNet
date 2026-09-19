"""Feature engineering for the forecasting panel (modular-plan.md §2.11).

panel.py (ml/data/) only ASSEMBLES raw joined columns; this module decides
what a forecaster may causally use. The rule enforced here: every feature
for predicting period T is built from data known no later than T-1 (a lag
of at least one period), except calendar features (month-of-year, ISO
week) which are always knowable in advance. This is what prevents the
same-period leakage that a naive "just join everything" panel would
invite.
"""
from __future__ import annotations

import pandas as pd

from backend.domain import Grain

# Real HMIS measurement columns that must be lagged, never used same-period.
_LAGGED_REAL_COLUMNS = [
    "balance_prev", "received", "unusable", "distributed", "total",
    "opd_attendance", "inpatient_midnight_census", "institutional_deliveries",
]

_LAGGED_SYNTHETIC_COLUMNS = ["on_hand_open", "received", "dispensed", "unusable", "on_hand_close"]


def _date_col(grain: Grain) -> str:
    return "month" if grain == Grain.DISTRICT_MONTH else "week"


def _entity_cols(grain: Grain) -> list[str]:
    return ["district_id", "drug_name"] if grain == Grain.DISTRICT_MONTH else ["facility_id", "drug_id"]


def add_lag_features(panel: pd.DataFrame, grain: Grain, lags: tuple[int, ...] = (1, 2, 3)) -> pd.DataFrame:
    """Adds `<col>_lag{k}` for each measurement column and each k in
    `lags`, grouped by entity and sorted by the date column.

    Builds an explicit ALLOWLIST of output columns (entity keys, date, lag
    columns) rather than starting from every panel column and blacklisting
    the ones known to be unsafe. panel.py (ml/data/) is free to add new
    joined columns over time (state_code, district_name, data-quality
    flags like balance_identity_ok, ...) -- a blacklist would silently let
    each new one leak into the feature matrix; this allowlist cannot."""
    df = panel.sort_values(_date_col(grain)).copy()
    entity_cols = _entity_cols(grain)
    date_col = _date_col(grain)
    measurement_cols = _LAGGED_REAL_COLUMNS if grain == Grain.DISTRICT_MONTH else _LAGGED_SYNTHETIC_COLUMNS
    measurement_cols = [c for c in measurement_cols if c in df.columns]

    grouped = df.groupby(entity_cols, sort=False)
    lag_cols = {}
    for col in measurement_cols:
        for lag in lags:
            lag_cols[f"{col}_lag{lag}"] = grouped[col].shift(lag)

    return pd.concat([df[[*entity_cols, date_col]], pd.DataFrame(lag_cols, index=df.index)], axis=1)


def add_calendar_features(panel: pd.DataFrame, grain: Grain) -> pd.DataFrame:
    """Month-of-year and a monsoon flag -- always knowable in advance, so
    safe to use same-period."""
    df = panel.copy()
    dates = pd.to_datetime(df[_date_col(grain)])
    df["month_of_year"] = dates.dt.month
    df["is_monsoon"] = dates.dt.month.isin([6, 7, 8, 9]).astype(int)
    return df


def build_features(panel: pd.DataFrame, grain: Grain, target_col: str, lags: tuple[int, ...] = (1, 2, 3)) -> pd.DataFrame:
    """The one function ml/forecast/*.py model files call. Returns the
    lagged, calendar-augmented feature frame with the (same-period, not
    leaked) target column re-attached for supervised training."""
    target = panel[[*_entity_cols(grain), _date_col(grain), target_col]].copy()
    df = add_lag_features(panel, grain, lags)
    df = add_calendar_features(df, grain)
    df = df.merge(target, on=[*_entity_cols(grain), _date_col(grain)], how="left")
    return df


def feature_columns(df: pd.DataFrame, target_col: str) -> tuple[str, ...]:
    """Stable, sorted tuple of feature column names (excludes identity and
    target columns) -- this is what ml/forecast/lgbm.py hashes into
    `features_hash` for the Forecast record."""
    exclude = {"district_id", "drug_name", "drug_id", "facility_id", "month", "week", target_col}
    return tuple(sorted(c for c in df.columns if c not in exclude))
