"""Combines forecasting models into one ensemble (modular-plan.md §2.11).

fit_weights() solves the exact linear program that minimizes WAPE on the
validation set over the convex simplex of member weights (w >= 0, sum
w = 1). Setting weight 1 on the best single member is itself a feasible
point of that simplex, so the LP's optimum can never be worse than the
best single member's validation WAPE -- this is what guarantees
test_ensemble.py's "ensemble WAPE <= best single member" property, rather
than relying on a heuristic (e.g. inverse-error weighting) that has no
such guarantee.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import linprog


@dataclass
class Ensemble:
    weights: dict[str, float] = field(default_factory=dict)

    def fit_weights(self, val_true: np.ndarray, val_predictions: dict[str, np.ndarray]) -> "Ensemble":
        names = list(val_predictions.keys())
        y = np.asarray(val_true, dtype=float)
        P = np.column_stack([np.asarray(val_predictions[n], dtype=float) for n in names])  # (N, M)
        n_obs, n_members = P.shape

        # variables: [w_1..w_M, t_1..t_N], minimize sum(t) / sum|y|
        # s.t. t_i >= y_i - sum_m w_m P_im,  t_i >= -(y_i - sum_m w_m P_im)
        #      sum(w) = 1, w >= 0, t >= 0
        c = np.concatenate([np.zeros(n_members), np.ones(n_obs)])
        A_ub_1 = np.hstack([P, -np.eye(n_obs)])          # y - Pw <= t  ->  -Pw - t <= -y
        A_ub_2 = np.hstack([-P, -np.eye(n_obs)])         # -(y - Pw) <= t -> Pw - t <= y
        A_ub = np.vstack([A_ub_1, A_ub_2])
        b_ub = np.concatenate([-y, y])
        A_eq = np.concatenate([np.ones(n_members), np.zeros(n_obs)]).reshape(1, -1)
        b_eq = np.array([1.0])
        bounds = [(0, None)] * n_members + [(0, None)] * n_obs

        result = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
        if not result.success:
            # fall back to putting all weight on the single best member --
            # still a feasible, still-guaranteed-no-worse-than-best point
            from eval.metrics import wape
            errors = {n: wape(y, val_predictions[n]) for n in names}
            best = min(errors, key=errors.get)
            self.weights = {n: (1.0 if n == best else 0.0) for n in names}
            return self

        raw_weights = result.x[:n_members]
        self.weights = dict(zip(names, raw_weights))
        return self

    def combine(self, predictions: dict[str, np.ndarray]) -> np.ndarray:
        if not self.weights:
            raise RuntimeError("call fit_weights() before combine()")
        stacked = np.zeros_like(next(iter(predictions.values())), dtype=float)
        for name, pred in predictions.items():
            stacked += self.weights.get(name, 0.0) * np.asarray(pred, dtype=float)
        return stacked
