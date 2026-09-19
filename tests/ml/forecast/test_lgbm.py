"""DoD test for ml/forecast/lgbm.py (step 17)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml.forecast.lgbm import LGBMForecaster, features_hash


def _toy_df(n=60, seed=0):
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    y = 3 * x1 - 2 * x2 + rng.normal(scale=0.1, size=n)
    return pd.DataFrame({
        "district_id": ["mh/nashik"] * n, "drug_name": ["ORS"] * n,
        "month": pd.date_range("2015-01-01", periods=n, freq="MS"),
        "feat1": x1, "feat2": x2, "distributed": y,
    })


def test_fit_predict_shape_contract():
    df = _toy_df()
    model = LGBMForecaster(target_col="distributed").fit(df)
    preds = model.predict(df)
    assert preds.shape == (len(df),)


def test_stable_feature_hash_is_reproducible():
    df = _toy_df()
    model = LGBMForecaster(target_col="distributed").fit(df)
    h1 = features_hash(model.columns)
    model2 = LGBMForecaster(target_col="distributed").fit(df.sample(frac=1, random_state=1))
    h2 = features_hash(model2.columns)
    assert h1 == h2


def test_no_target_column_in_feature_matrix():
    df = _toy_df()
    model = LGBMForecaster(target_col="distributed").fit(df)
    assert "distributed" not in model.columns


def test_predict_before_fit_raises():
    model = LGBMForecaster(target_col="distributed")
    with pytest.raises(RuntimeError):
        model.predict(_toy_df())


def test_fit_learns_a_real_relationship():
    """Not just a shape check: the model should actually predict better
    than a constant mean on this synthetic linear-ish relationship."""
    df = _toy_df(n=200)
    train, test = df.iloc[:150], df.iloc[150:]
    model = LGBMForecaster(target_col="distributed").fit(train)
    preds = model.predict(test)
    mean_baseline_error = np.abs(test["distributed"] - train["distributed"].mean()).mean()
    model_error = np.abs(test["distributed"].to_numpy() - preds).mean()
    assert model_error < mean_baseline_error
