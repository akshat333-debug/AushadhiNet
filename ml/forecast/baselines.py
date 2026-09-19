"""Baseline forecasters (modular-plan.md §2.11): seasonal naive and moving
average. Every real model is compared against these; a model that cannot
beat seasonal naive on the frozen test window is reported as such, not
hidden (project.md §7 / AC4).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def seasonal_naive(history: pd.Series, horizon: int, season_length: int = 1) -> np.ndarray:
    """Forecast the next `horizon` points as a repeat of the last full
    season. With season_length=1 this is the plain last-value-carried-
    forward naive forecast."""
    if len(history) < season_length:
        raise ValueError("history shorter than season_length")
    last_season = history.iloc[-season_length:].to_numpy()
    reps = int(np.ceil(horizon / season_length))
    return np.tile(last_season, reps)[:horizon]


def moving_average(history: pd.Series, horizon: int, window: int = 3) -> np.ndarray:
    """Flat forecast at the mean of the last `window` observations."""
    if len(history) == 0:
        raise ValueError("empty history")
    window = min(window, len(history))
    avg = float(history.iloc[-window:].mean())
    return np.full(horizon, avg)
