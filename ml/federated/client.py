"""A Flower NumPyClient wrapping a linear regression head (modular-plan.md
§2.13). A linear head, not the LightGBM tree ensemble, is what is
federated: tree parameters cannot be meaningfully weight-averaged the way
FedAvg/FedProx requires, so the federated arm compares a linear model
against itself across local-only/federated/centralised training, which is
the fair comparison (project.md's federation demonstration is about the
cross-state learning mechanism, not about out-forecasting LightGBM).

FedProx's proximal term keeps a client's local update from drifting too
far from the global model between rounds -- important here because
states have very different data volumes (Maharashtra has decades of
history; Meghalaya, project.md's data-poor state, has much less). DP
clip+noise (ml/federated/dp.py) is applied to the parameter DELTA before
it ever leaves this client (AC9).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from flwr.client import NumPyClient

from backend.domain import Grain

from ml.federated.dp import clip_and_noise
from ml.forecast.features import build_features, feature_columns


def _design_matrix(panel: pd.DataFrame, target_col: str) -> tuple[np.ndarray, np.ndarray, tuple[str, ...]]:
    featured = build_features(panel, Grain.DISTRICT_MONTH, target_col=target_col)
    supervised = featured.dropna(subset=[target_col])
    cols = feature_columns(featured, target_col)
    # log1p space: states differ in volume by orders of magnitude, so raw-level
    # weights don't transfer; log-space shapes do (chosen on an inner split of
    # the train window, see eval/tune_federated.py).
    X = np.log1p(supervised[list(cols)].fillna(0.0).clip(lower=0).to_numpy(dtype=float))
    y = np.log1p(supervised[target_col].clip(lower=0).to_numpy(dtype=float))
    return X, y, cols


class LinearHeadClient(NumPyClient):
    """Closed-form ridge regression with a FedProx proximal term, not
    iterative gradient descent: local features span vastly different
    scales (raw lag values of `distributed` range from single digits to
    hundreds of thousands), and a fixed learning rate that is stable for
    one scale diverges on another -- ridge's normal equations have no
    step-size to tune and cannot diverge this way. Standardises features
    per client before solving (each client's own mean/std, since that is
    exactly the kind of statistic that never leaves the client)."""

    def __init__(
        self, state_code: str, panel: pd.DataFrame, target_col: str = "distributed",
        proximal_mu: float = 0.0, clip_norm: float = 1e6, noise_multiplier: float = 0.0,
        ridge_lambda: float = 1.0, local_epochs: int = 1, seed: int = 0,
        feature_mean: np.ndarray | None = None, feature_std: np.ndarray | None = None,
    ):
        """`feature_mean`/`feature_std`, if given, override this client's
        own statistics. Federation REQUIRES this: if every client (and
        the held-out evaluation client) standardises with its own local
        mean/std, a weight vector learned on one client's feature scale
        is silently wrong when applied to another's -- this was a real
        bug caught by comparing arms in ml/federated/experiments.py
        (federated/centralised scored far worse than local-only, which
        traced back to exactly this mismatch, not to the aggregation
        itself). The local-only arm is the one case where self-computed
        stats are correct, since the same state's data is used for both
        fitting and evaluating it."""
        self.state_code = state_code
        X_raw, self.y, self.columns = _design_matrix(panel, target_col)
        self.feature_mean = feature_mean if feature_mean is not None else (X_raw.mean(axis=0) if X_raw.size else np.zeros(0))
        self.feature_std = feature_std if feature_std is not None else (
            np.where(X_raw.std(axis=0) > 1e-9, X_raw.std(axis=0), 1.0) if X_raw.size else np.ones(0)
        )
        self.X = (X_raw - self.feature_mean) / self.feature_std if X_raw.size else X_raw
        self.proximal_mu = proximal_mu
        self.clip_norm = clip_norm
        self.noise_multiplier = noise_multiplier
        self.ridge_lambda = ridge_lambda
        self.local_epochs = local_epochs  # kept for interface parity; unused by closed-form solve
        self.rng = np.random.default_rng(seed)
        self.n_features = self.X.shape[1] if self.X.size else 0

    def get_parameters(self, config: dict) -> list[np.ndarray]:
        return [np.zeros(self.n_features + 1)]  # weights + bias, initial

    def fit(self, parameters: list[np.ndarray], config: dict) -> tuple[list[np.ndarray], int, dict]:
        w0 = parameters[0].copy()
        n = len(self.y)
        if n == 0:
            return [w0], 0, {"loss": float("nan")}

        X_aug = np.hstack([self.X, np.ones((n, 1))])
        reg = (self.ridge_lambda + self.proximal_mu) * np.eye(self.n_features + 1)
        rhs = X_aug.T @ self.y + self.proximal_mu * w0
        w = np.linalg.solve(X_aug.T @ X_aug + reg, rhs)

        delta = [w - w0]
        if self.noise_multiplier > 0 or self.clip_norm < 1e6:
            delta = clip_and_noise(delta, self.clip_norm, self.noise_multiplier, self.rng)
        new_w = w0 + delta[0]

        final_pred = X_aug @ new_w
        loss = float(np.mean(np.abs(final_pred - self.y)))
        return [new_w], n, {"loss": loss, "state": self.state_code}

    def evaluate(self, parameters: list[np.ndarray], config: dict) -> tuple[float, int, dict]:
        w = parameters[0]
        if len(self.y) == 0:
            return float("nan"), 0, {}
        X_aug = np.hstack([self.X, np.ones((len(self.y), 1))])
        from eval.metrics import wape
        score = float(wape(np.expm1(self.y), np.expm1(X_aug @ w)))
        return score, len(self.y), {"wape": score}


def make(state_code: str, panel: pd.DataFrame, **kwargs) -> LinearHeadClient:
    return LinearHeadClient(state_code, panel, **kwargs)
