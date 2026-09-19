"""DoD test for ml/forecast/calibration.py (step 19, AC5)."""
from __future__ import annotations

import numpy as np

from ml.forecast.calibration import Calibrator, brier_improvement, fit


def _miscalibrated_data(n=500, seed=0):
    rng = np.random.default_rng(seed)
    true_prob = rng.uniform(0, 1, n)
    outcomes = (rng.random(n) < true_prob).astype(float)
    # systematically overconfident: push raw probs toward the extremes
    raw_probs = np.clip(0.5 + 1.8 * (true_prob - 0.5), 0.0, 1.0)
    return raw_probs, outcomes


def test_brier_after_calibration_is_no_worse_on_validation():
    raw_probs, outcomes = _miscalibrated_data()
    calibrator = fit(raw_probs, outcomes)
    before, after = brier_improvement(raw_probs, outcomes, calibrator)
    assert after <= before + 1e-9


def test_calibrator_output_is_monotone_in_input():
    raw_probs, outcomes = _miscalibrated_data()
    calibrator = fit(raw_probs, outcomes)
    order = np.argsort(raw_probs)
    calibrated_sorted = calibrator.transform(raw_probs[order])
    assert np.all(np.diff(calibrated_sorted) >= -1e-9)


def test_transform_before_fit_raises():
    import pytest
    c = Calibrator()
    with pytest.raises(RuntimeError):
        c.transform(np.array([0.5]))


def test_output_bounded_0_1():
    raw_probs, outcomes = _miscalibrated_data()
    calibrator = fit(raw_probs, outcomes)
    out = calibrator.transform(np.array([-1.0, 0.0, 0.5, 1.0, 2.0]))
    assert (out >= 0.0).all() and (out <= 1.0).all()
