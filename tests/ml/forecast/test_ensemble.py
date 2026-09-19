"""DoD test for ml/forecast/timesfm_zs.py, ensemble.py, registry.py (step 18)."""
from __future__ import annotations

import numpy as np
import pytest

from ml.forecast.ensemble import Ensemble
from ml.forecast.registry import MODEL_REGISTRY, get_model
from ml.forecast.timesfm_zs import is_available as timesfm_available


def test_ensemble_beats_or_matches_best_single_member_on_validation():
    rng = np.random.default_rng(0)
    val_true = 10 + rng.normal(0, 1, 50)
    # one good member (small noise), one bad member (large bias)
    good = val_true + rng.normal(0, 0.2, 50)
    bad = val_true + 5.0
    ens = Ensemble().fit_weights(val_true, {"good": good, "bad": bad})

    from eval.metrics import wape
    ensemble_pred = ens.combine({"good": good, "bad": bad})
    ensemble_wape = wape(val_true, ensemble_pred)
    best_single_wape = min(wape(val_true, good), wape(val_true, bad))
    assert ensemble_wape <= best_single_wape + 1e-9


def test_ensemble_weights_sum_to_one():
    val_true = np.array([10.0, 20.0, 30.0])
    ens = Ensemble().fit_weights(val_true, {"a": val_true, "b": val_true * 2})
    assert sum(ens.weights.values()) == pytest.approx(1.0)


def test_ensemble_downweights_bad_member_near_zero():
    val_true = np.full(20, 10.0)
    good = val_true.copy()
    terrible = val_true + 1000.0
    ens = Ensemble().fit_weights(val_true, {"good": good, "terrible": terrible})
    assert ens.weights["good"] > 0.99
    assert ens.weights["terrible"] < 0.01


def test_combine_before_fit_raises():
    ens = Ensemble()
    with pytest.raises(RuntimeError):
        ens.combine({"a": np.array([1.0])})


def test_registry_has_always_available_models():
    for name in ("seasonal_naive", "moving_average", "croston", "lgbm"):
        assert name in MODEL_REGISTRY
    model = get_model("seasonal_naive")
    assert callable(model)


def test_registry_rejects_unknown_model():
    with pytest.raises(KeyError):
        get_model("not-a-real-model")


def test_timesfm_availability_check_does_not_raise():
    # must not attempt a network download just to check availability
    result = timesfm_available()
    assert isinstance(result, bool)
