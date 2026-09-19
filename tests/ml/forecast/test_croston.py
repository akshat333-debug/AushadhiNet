"""DoD test for ml/forecast/croston.py + arima_bqml.py (step 16)."""
from __future__ import annotations

import numpy as np
import pytest

from backend.config import get_settings
from ml.forecast.arima_bqml import fit_predict_sql, is_available
from ml.forecast.croston import fit_predict, intermittency_rate


def test_intermittent_series_gives_positive_non_degenerate_rate():
    rng = np.random.default_rng(0)
    history = np.where(rng.random(60) < 0.2, rng.uniform(1, 5, 60), 0.0)  # ~80% zeros
    assert intermittency_rate(history) == pytest.approx(0.8, abs=0.1)

    forecast = fit_predict(history, horizon=4)
    assert len(forecast) == 4
    assert (forecast > 0).all()
    assert np.all(forecast == forecast[0])  # Croston is a flat rate forecast


def test_intermittency_rate_of_empty_is_zero():
    assert intermittency_rate(np.array([])) == 0.0


def test_fit_predict_rejects_empty_history():
    with pytest.raises(ValueError):
        fit_predict(np.array([]), horizon=1)


@pytest.mark.skipif(not is_available(get_settings().mode), reason="ARIMA_PLUS: not run (cloud only)")
def test_arima_plus_runs_only_in_cloud_mode():
    pytest.fail("this test only runs when AUSHADHI_MODE=cloud, which local CI never sets")


def test_is_available_only_true_for_cloud_mode():
    assert is_available("cloud") is True
    assert is_available("local") is False


def test_arima_sql_shape_is_well_formed():
    sql = fit_predict_sql("proj.ds.stock", "month", "distributed", ["district_id", "drug_id"], horizon=6)
    assert "CREATE OR REPLACE MODEL" in sql
    assert "ARIMA_PLUS" in sql
    assert "ML.FORECAST" in sql
    assert "district_id" in sql and "drug_id" in sql
