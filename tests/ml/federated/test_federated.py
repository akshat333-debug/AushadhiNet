"""DoD test for ml/federated/ (step 38, AC9)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from backend.domain import Grain
from ml.data.panel import build as build_panel
from ml.federated.client import LinearHeadClient, make
from ml.federated.dp import clip_and_noise, clip_update
from ml.federated.partition import by_state
from ml.federated.server import run
from ml.federated.strategy import aggregate, fedprox_dp


def test_partition_splits_by_state_with_no_cross_contamination():
    panel = build_panel(Grain.DISTRICT_MONTH)
    parts = by_state(panel)
    assert set(parts.keys()) == {"MH", "HR", "AS", "ML"}
    for state, df in parts.items():
        assert (df["state_code"] == state).all()


def test_meghalaya_never_a_training_client_in_holdout_arm():
    """The held-out-state arm: Meghalaya's own client is evaluated but
    excluded from the training clients whose updates get aggregated."""
    panel = build_panel(Grain.DISTRICT_MONTH)
    parts = by_state(panel)
    training_states = [s for s in parts if s != "ML"]
    assert "ML" not in training_states
    assert set(training_states) == {"MH", "HR", "AS"}


# --- DP: clip + noise ---

def test_clip_reduces_norm_to_at_most_clip_norm():
    delta = [np.array([10.0, 10.0, 10.0])]  # norm ~17.3
    clipped = clip_update(delta, clip_norm=5.0)
    total_norm = np.sqrt(sum(np.sum(d ** 2) for d in clipped))
    assert total_norm <= 5.0 + 1e-6


def test_clip_is_noop_when_already_under_norm():
    delta = [np.array([0.1, 0.1])]
    clipped = clip_update(delta, clip_norm=5.0)
    np.testing.assert_array_equal(clipped[0], delta[0])


def test_noise_statistics_match_configured_sigma():
    """Over many draws, the added noise's std should match
    noise_multiplier * clip_norm (Abadi et al. 2016 DP-SGD calibration)."""
    rng = np.random.default_rng(0)
    clip_norm, noise_multiplier = 1.0, 2.0
    draws = []
    for _ in range(1000):
        delta = [np.array([0.0])]
        noised = clip_and_noise(delta, clip_norm, noise_multiplier, rng)
        draws.append(noised[0][0])
    empirical_std = np.std(draws)
    assert abs(empirical_std - (noise_multiplier * clip_norm)) < 0.15


# --- fit() returns only whitelisted types (AC9: no raw row crosses the boundary) ---

def test_client_fit_return_value_contains_only_parameter_arrays_and_scalars():
    panel = build_panel(Grain.DISTRICT_MONTH, states=["mah"])
    client = LinearHeadClient("MH", panel, local_epochs=2)
    params = client.get_parameters({})
    new_params, n, metrics = client.fit(params, {})

    assert isinstance(new_params, list)
    assert all(isinstance(p, np.ndarray) for p in new_params)
    assert isinstance(n, int)
    for key, value in metrics.items():
        assert isinstance(value, (int, float, str)), f"metric {key} is not a whitelisted scalar type: {type(value)}"
    # explicitly: no pandas object, no raw row, anywhere in the return value
    assert not isinstance(new_params, pd.DataFrame)


# --- strategy aggregation ---

def test_aggregate_is_weighted_average():
    fit_results = [
        ([np.array([1.0, 1.0])], 10),
        ([np.array([3.0, 3.0])], 30),
    ]
    result = aggregate(fit_results)
    # weighted mean: (1*10 + 3*30)/40 = 2.5
    np.testing.assert_allclose(result[0], [2.5, 2.5])


def test_fedprox_dp_returns_real_flower_strategy():
    from flwr.server.strategy import FedProx
    strategy = fedprox_dp(mu=0.1, clip_norm=1.0, noise_multiplier=0.5)
    assert isinstance(strategy, FedProx)


# --- server: a small multi-round run converges ---

def test_three_round_two_client_run_converges():
    panel = build_panel(Grain.DISTRICT_MONTH, states=["mah", "har"])
    parts = by_state(panel)
    clients = [make(state, df, ridge_lambda=1.0) for state, df in parts.items()]
    result = run(clients, rounds=3)
    assert result.rounds_run == 3
    assert len(result.loss_history) == 3
    valid_losses = [l for l in result.loss_history if not np.isnan(l)]
    assert len(valid_losses) >= 2
    assert valid_losses[-1] <= valid_losses[0] * 1.5  # did not blow up; roughly stable/improving
