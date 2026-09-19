"""Validation-window model selection for the real-HMIS forecaster.

Fits on the train window, scores on the validation window, never touches
test rows (it only uses Split.train_mask / val_mask). The candidate list is
fixed here up front so the search is small and auditable; the winner's
params are what ml/forecast/lgbm.py ships as defaults.
"""
from __future__ import annotations

import lightgbm as lgb
import numpy as np

from backend.domain import Grain
from eval.metrics import wape
from eval.protocol import load_protocol
from eval.splits import for_grain
from ml.data.panel import build as build_panel
from ml.forecast.features import build_features, feature_columns

TARGET = "distributed"
TUNED = {"n_estimators": 300, "learning_rate": 0.03, "num_leaves": 15, "min_child_samples": 20,
         "subsample": 0.8, "subsample_freq": 1, "colsample_bytree": 0.8, "random_state": 0}
OLD = {"n_estimators": 100, "max_depth": 5, "min_child_samples": 5}
CANDIDATES = {
    "lgbm_l2_old_params": {"objective": "l2", **OLD},
    "lgbm_l1_old_params": {"objective": "l1", **OLD},
    "lgbm_l2_tuned": {"objective": "l2", **TUNED},
    "lgbm_l1_tuned": {"objective": "l1", **TUNED},
}


def main() -> dict[str, float]:
    featured = build_features(build_panel(Grain.DISTRICT_MONTH, states=["mah"]), Grain.DISTRICT_MONTH, TARGET)
    split = for_grain(Grain.DISTRICT_MONTH, load_protocol())
    train = featured[split.train_mask(featured)].dropna(subset=[TARGET])
    val = featured[split.val_mask(featured)].dropna(subset=[TARGET])
    cols = list(feature_columns(featured, TARGET))
    y = val[TARGET].to_numpy()
    lags = [f"{TARGET}_lag{k}" for k in (1, 2, 3)]

    scores = {
        "naive_lag1": wape(y, val[lags[0]].fillna(train[TARGET].mean()).to_numpy()),
        "median3": wape(y, val[lags].median(axis=1).fillna(train[TARGET].median()).to_numpy()),
    }
    for name, params in CANDIDATES.items():
        model = lgb.LGBMRegressor(verbosity=-1, **params).fit(train[cols], train[TARGET])
        scores[name] = wape(y, model.predict(val[cols]))
    for name, score in sorted(scores.items(), key=lambda kv: kv[1]):
        print(f"{name:22s} val WAPE {score:.4f}")
    return scores


if __name__ == "__main__":
    main()
