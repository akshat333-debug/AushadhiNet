"""Model name -> fit/predict lookup (modular-plan.md §2.11), so callers
(eval/run_backtest.py, eval/run_final.py, backend/agent tools) refer to
models by a stable string rather than importing each module directly.
"""
from __future__ import annotations

from ml.forecast.baselines import moving_average, seasonal_naive
from ml.forecast.croston import fit_predict as croston_fit_predict
from ml.forecast.lgbm import LGBMForecaster
from ml.forecast.timesfm_zs import fit_predict as timesfm_fit_predict
from ml.forecast.timesfm_zs import is_available as timesfm_is_available

MODEL_REGISTRY = {
    "seasonal_naive": seasonal_naive,
    "moving_average": moving_average,
    "croston": croston_fit_predict,
    "lgbm": LGBMForecaster,
    "timesfm": timesfm_fit_predict,
}


def get_model(name: str):
    if name not in MODEL_REGISTRY:
        raise KeyError(f"unknown model '{name}'. Known models: {sorted(MODEL_REGISTRY)}")
    if name == "timesfm" and not timesfm_is_available():
        raise KeyError(
            "model 'timesfm' is registered but no backend (torch/jax) is installed. "
            "It is an optional ensemble member -- omit it rather than treating this as a bug."
        )
    return MODEL_REGISTRY[name]
