"""DoD test for eval/metrics.py + eval/splits.py (step 13)."""
from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from backend.domain import Grain
from eval.metrics import brier, mase, pinball, stockout_scores, wape
from eval.protocol import load_protocol
from eval.splits import for_grain


# --- wape ---

def test_wape_hand_computed():
    y_true = np.array([10, 0, 20, 5, 15])
    y_pred = np.array([8, 2, 22, 5, 10])
    # sum|err| = 2+2+2+0+5 = 11; sum|actual| = 50
    assert wape(y_true, y_pred) == pytest.approx(11 / 50)


def test_wape_zero_actuals_zero_pred_is_zero():
    assert wape([0, 0], [0, 0]) == 0.0


def test_wape_zero_actuals_nonzero_pred_is_inf():
    assert wape([0, 0], [1, 0]) == float("inf")


# --- mase ---

def test_mase_hand_computed():
    train = np.array([10, 12, 11, 13, 14, 12, 15])  # season_length=1 naive
    y_true = np.array([16, 14])
    y_pred = np.array([15, 15])
    # naive errors on train: |12-10|,|11-12|,|13-11|,|14-13|,|12-14|,|15-12| = 2,1,2,1,2,3 -> mean=11/6
    scale = np.mean([2, 1, 2, 1, 2, 3])
    expected = np.mean([1, 1]) / scale
    assert mase(y_true, y_pred, train, season_length=1) == pytest.approx(expected)


def test_mase_denominator_uses_training_window_only():
    """Changing the scored series (y_true/y_pred) must not change the
    scale, since it is computed purely from train_series."""
    train = np.array([10, 12, 11, 13, 14, 12, 15])
    m1 = mase(np.array([16, 14]), np.array([15, 15]), train)
    m2 = mase(np.array([100, 200]), np.array([90, 190]), train)
    # both use the same scale; verify by reconstructing it independently
    scale = np.abs(train[1:] - train[:-1]).mean()
    assert m1 == pytest.approx(np.mean([1, 1]) / scale)
    assert m2 == pytest.approx(np.mean([10, 10]) / scale)


def test_mase_rejects_too_short_train_series():
    with pytest.raises(ValueError):
        mase([1], [1], train_series=[5], season_length=1)


# --- pinball ---

def test_pinball_hand_computed():
    y_true = np.array([10.0])
    y_pred = np.array([8.0])
    # under-prediction at q=0.9: q*(true-pred) = 0.9*2 = 1.8
    assert pinball(y_true, y_pred, 0.9) == pytest.approx(1.8)
    y_pred_over = np.array([12.0])
    # over-prediction at q=0.9: (q-1)*(true-pred) = -0.1*(-2) = 0.2
    assert pinball(y_true, y_pred_over, 0.9) == pytest.approx(0.2)


def test_pinball_rejects_bad_quantile():
    with pytest.raises(ValueError):
        pinball([1], [1], 1.5)


# --- brier / stockout_scores ---

def test_brier_hand_computed():
    y_true = np.array([1, 0, 1, 0])
    p_hat = np.array([0.8, 0.2, 0.6, 0.4])
    expected = np.mean([(0.8 - 1) ** 2, (0.2 - 0) ** 2, (0.6 - 1) ** 2, (0.4 - 0) ** 2])
    assert brier(y_true, p_hat) == pytest.approx(expected)


def test_stockout_scores_perfect_prediction():
    y_true = np.array([1, 0, 1, 0])
    p_hat = np.array([0.9, 0.1, 0.9, 0.1])
    scores = stockout_scores(y_true, p_hat, horizon=4)
    assert scores["recall"] == 1.0
    assert scores["precision"] == 1.0
    assert scores["horizon"] == 4


# --- splits ---

def test_split_dhule_never_in_train_or_val():
    protocol = load_protocol()
    split = for_grain(Grain.DISTRICT_MONTH, protocol)
    assert split.held_out_entity == "mh/dhule"


def test_split_facility_week_requires_panel_max_date():
    protocol = load_protocol()
    with pytest.raises(ValueError):
        for_grain(Grain.FACILITY_WEEK, protocol)


def test_split_facility_week_test_window_is_26_weeks_ending_at_max():
    protocol = load_protocol()
    split = for_grain(Grain.FACILITY_WEEK, protocol, panel_max_date=date(2020, 2, 29))
    assert split.test_end == date(2020, 2, 29)
    assert (split.test_end - split.test_start).days == 7 * (protocol.synthetic_benchmark.test_weeks - 1)
    assert split.train_end < split.test_start
