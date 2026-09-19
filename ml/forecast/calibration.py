"""Isotonic calibration of stock-out probabilities (modular-plan.md §2.11,
AC5). Raw model probabilities are rarely well-calibrated; isotonic
regression fits a monotone map from raw probability to observed frequency
on a validation set.
"""
from __future__ import annotations

import numpy as np
from sklearn.isotonic import IsotonicRegression

from eval.metrics import brier


class Calibrator:
    def __init__(self):
        self._iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        self._fitted = False

    def fit(self, val_probs: np.ndarray, val_outcomes: np.ndarray) -> "Calibrator":
        self._iso.fit(np.asarray(val_probs, dtype=float), np.asarray(val_outcomes, dtype=float))
        self._fitted = True
        return self

    def transform(self, probs: np.ndarray) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("call fit() before transform()")
        return self._iso.predict(np.asarray(probs, dtype=float))


def fit(val_probs: np.ndarray, val_outcomes: np.ndarray) -> Calibrator:
    return Calibrator().fit(val_probs, val_outcomes)


def brier_improvement(val_probs: np.ndarray, val_outcomes: np.ndarray, calibrator: Calibrator) -> tuple[float, float]:
    """Returns (brier_before, brier_after) on the SAME validation set the
    calibrator was fit on -- AC5's check is that calibration cannot make
    validation calibration worse, not that it generalizes further (that is
    what the held-out test-window run separately verifies)."""
    before = brier(val_outcomes, val_probs)
    after = brier(val_outcomes, calibrator.transform(val_probs))
    return before, after
