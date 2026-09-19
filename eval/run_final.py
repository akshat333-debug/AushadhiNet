"""Scores the FROZEN test window -- exactly once per invocation, appended
to eval/reports/runs.jsonl (modular-plan.md §2.10, step 21). This is the
only file in the whole project allowed to compute a metric on test-window
rows (architecture.md §5); eval/run_backtest.py refuses to even hand out
that data.

This is where AC4 ("forecaster beats seasonal-naive WAPE on the real-HMIS
frozen test window, reported honestly either way") gets its actual
answer: whichever way the comparison goes, both rows are written and
neither run overwrites the other.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import uuid
from datetime import datetime, timezone

import numpy as np

from backend.domain import Grain

from eval.metrics import mase, wape
from eval.protocol import load_protocol
from eval.splits import for_grain
from ml.data.panel import build as build_panel
from ml.forecast.features import build_features
from ml.forecast.lgbm import LGBMForecaster

REPORTS_PATH = pathlib.Path(__file__).resolve().parent / "reports" / "runs.jsonl"


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=pathlib.Path(__file__).resolve().parents[1],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "no-commits-yet"


def _predict_seasonal_naive(train_df, test_df, target_col: str) -> np.ndarray:
    """Lag-1 naive (season_length=1): this period's forecast is last
    period's actual. Name kept for continuity with earlier runs.jsonl rows."""
    fallback = float(train_df[target_col].mean())
    return test_df[f"{target_col}_lag1"].fillna(fallback).to_numpy()


def _predict_median3(train_df, test_df, target_col: str) -> np.ndarray:
    """Median of the last 3 actuals -- a tougher robust baseline for lumpy issuance."""
    fallback = float(train_df[target_col].median())
    lags = [f"{target_col}_lag{k}" for k in (1, 2, 3)]
    return test_df[lags].median(axis=1).fillna(fallback).to_numpy()


def compute_metrics(
    model_name: str,
    grain: Grain = Grain.DISTRICT_MONTH,
    states: tuple[str, ...] = ("mah",),
    target_col: str = "distributed",
) -> dict:
    protocol = load_protocol()
    panel = build_panel(grain, states=list(states))
    featured = build_features(panel, grain, target_col=target_col)

    date_col = "month" if grain == Grain.DISTRICT_MONTH else "week"
    panel_max_date = None
    if grain == Grain.FACILITY_WEEK:
        import pandas as pd
        panel_max_date = pd.to_datetime(panel[date_col]).max().date()
    split = for_grain(grain, protocol, panel_max_date=panel_max_date)

    # Hyperparameters were picked on train->val; the final fit uses train+val,
    # which ends before the test window starts.
    train_df = featured[split.train_mask(featured) | split.val_mask(featured)]
    test_df = featured[split.test_mask(featured)].dropna(subset=[target_col])
    if test_df.empty:
        raise RuntimeError("test window is empty -- check the panel covers the frozen test dates")

    if model_name == "seasonal_naive":
        preds = _predict_seasonal_naive(train_df, test_df, target_col)
    elif model_name == "median3":
        preds = _predict_median3(train_df, test_df, target_col)
    elif model_name == "lgbm":
        model = LGBMForecaster(target_col=target_col).fit(train_df)
        preds = model.predict(test_df)
    else:
        raise ValueError(f"unsupported model for run_final: {model_name}")

    y_true = test_df[target_col].to_numpy()
    train_series = train_df[target_col].dropna().to_numpy()
    metrics = {
        "wape": wape(y_true, preds),
        "mase": mase(y_true, preds, train_series=train_series) if len(train_series) > 1 else None,
        "n_test_rows": int(len(test_df)),
    }
    return metrics


def append_run(model_name: str, grain: Grain = Grain.DISTRICT_MONTH, reports_path: pathlib.Path = REPORTS_PATH) -> dict:
    protocol = load_protocol()
    metrics = compute_metrics(model_name, grain)
    record = {
        "run_id": str(uuid.uuid4()),
        "git_sha": _git_sha(),
        "model": model_name,
        "grain": grain.value,
        "metrics": metrics,
        "protocol_hash": protocol.generator_seal.content_hash,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    reports_path.parent.mkdir(parents=True, exist_ok=True)
    with open(reports_path, "a") as f:
        f.write(json.dumps(record) + "\n")
    return record


def main(model_name: str = "lgbm") -> None:
    for name in ("seasonal_naive", "median3", model_name):
        print(f"{name}: {append_run(name)['metrics']}")


if __name__ == "__main__":
    main()
