"""Croston/SBA for intermittent (zero-heavy) demand series (modular-plan.md
§2.11), via statsforecast. PHC drug demand at facility-week granularity is
often mostly zeros -- plain seasonal-naive or moving-average forecasts
degenerate on that, which is exactly the case Croston's method targets.
"""
from __future__ import annotations

import numpy as np
from statsforecast.models import CrostonSBA


def fit_predict(history: np.ndarray, horizon: int) -> np.ndarray:
    """Fits Croston-SBA on `history` and returns a flat `horizon`-length
    forecast (Croston's method is a rate estimate, not a per-step-varying
    curve, so every future step gets the same predicted rate)."""
    history = np.asarray(history, dtype=float)
    if len(history) == 0:
        raise ValueError("empty history")
    model = CrostonSBA()
    model.fit(history)
    result = model.predict(h=horizon)
    return np.asarray(result["mean"], dtype=float)


def intermittency_rate(history: np.ndarray) -> float:
    """Fraction of periods with zero demand -- used to decide whether
    Croston is the right tool for a given series (ml/forecast/ensemble.py)."""
    history = np.asarray(history, dtype=float)
    if len(history) == 0:
        return 0.0
    return float(np.mean(history == 0))
