"""BigQuery ML ARIMA_PLUS baseline (modular-plan.md §2.11).

ARIMA_PLUS is a managed BigQuery model with no local (DuckDB) equivalent
-- architecture.md §5 gap #4. Every committed evaluation run is local, so
this baseline is explicitly skipped there and reported as "not run (cloud
only)" rather than silently omitted from the results table (data
integrity: a missing baseline row must never look like a decision to
leave it out).

This module never reads os.environ itself (architecture.md §2: only
backend/config.py may) -- `is_available(mode)` takes the mode as an
explicit argument, which callers get from backend.config.get_settings().
"""
from __future__ import annotations


def is_available(mode: str) -> bool:
    """True only in "cloud" mode, where a real BigQuery connection exists."""
    return mode == "cloud"


def fit_predict_sql(table: str, time_col: str, target_col: str, id_cols: list[str], horizon: int) -> str:
    """Returns the BigQuery ML SQL to train and forecast ARIMA_PLUS. Not
    executed locally -- this function only builds the SQL string, so it is
    testable (the SQL shape) without a BigQuery connection."""
    id_col_sql = ", ".join(id_cols)
    return f"""
CREATE OR REPLACE MODEL `{table}_arima_plus`
OPTIONS (
  model_type = 'ARIMA_PLUS',
  time_series_timestamp_col = '{time_col}',
  time_series_data_col = '{target_col}',
  time_series_id_col = [{", ".join(f"'{c}'" for c in id_cols)}]
) AS
SELECT {time_col}, {target_col}, {id_col_sql}
FROM `{table}`;

SELECT *
FROM ML.FORECAST(MODEL `{table}_arima_plus`, STRUCT({horizon} AS horizon));
""".strip()
