"""LightGBM global forecaster (modular-plan.md §2.11). Trained locally
with the sklearn API in every committed run (architecture.md §5 gap #3:
Vertex AI custom training is a post-credits deployment target, not on the
critical path -- AC10 forbids requiring GCP).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

import lightgbm as lgb
import numpy as np
import pandas as pd

from ml.forecast.features import feature_columns


def features_hash(columns: tuple[str, ...]) -> str:
    """Stable hash of the sorted feature-column tuple, recorded on every
    Forecast so a prediction can be traced back to exactly what inputs
    produced it."""
    return hashlib.sha256("|".join(columns).encode()).hexdigest()[:16]


@dataclass
class LGBMForecaster:
    target_col: str
    params: dict | None = None
    model: lgb.LGBMRegressor | None = None
    columns: tuple[str, ...] | None = None

    def fit(self, train_df: pd.DataFrame) -> "LGBMForecaster":
        cols = feature_columns(train_df, self.target_col)
        if any(c == self.target_col for c in cols):
            raise ValueError("target column leaked into the feature set")
        supervised = train_df.dropna(subset=[self.target_col])
        X = supervised[list(cols)]
        y = supervised[self.target_col]

        # L1 objective: WAPE is minimised by the conditional median, not the mean.
        # Chosen on the validation window only (eval/tune_val.py), never the test window.
        default_params = {
            "objective": "l1", "n_estimators": 300, "learning_rate": 0.03, "num_leaves": 15,
            "min_child_samples": 20, "subsample": 0.8, "subsample_freq": 1,
            "colsample_bytree": 0.8, "random_state": 0, "verbosity": -1,
        }
        model = lgb.LGBMRegressor(**(self.params or default_params))
        model.fit(X, y)

        self.model, self.columns = model, cols
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        if self.model is None or self.columns is None:
            raise RuntimeError("call fit() before predict()")
        X = df[list(self.columns)]
        return self.model.predict(X)
