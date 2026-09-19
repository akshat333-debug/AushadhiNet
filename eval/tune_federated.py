"""Hyperparameter check for the federated linear head, on an INNER split
of the train window (inner-train < 2018-09, inner-val 2018-09..2019-02).

eval/run_federated_eval.py reports on the protocol validation window, so
tuning there would optimise the reported number. This script never reads
validation or test rows.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from backend.domain import Grain
from eval.protocol import load_protocol
from eval.splits import for_grain
from ml.data.panel import build as build_panel
from ml.federated.client import LinearHeadClient
from ml.federated.experiments import _STATE_CODE_MAP, _global_stats
from ml.federated.partition import by_state

INNER_CUTOFF = pd.Timestamp("2018-09-01")
LAMBDAS = (0.1, 1.0, 10.0, 100.0)


def main() -> dict[float, dict[str, float]]:
    protocol = load_protocol()
    panel = build_panel(Grain.DISTRICT_MONTH)
    train = panel[for_grain(Grain.DISTRICT_MONTH, protocol).train_mask(panel)]
    # Inner-val keeps its history so lag features exist; only its target rows are scored.
    inner_tr = train[pd.to_datetime(train["month"]) < INNER_CUTOFF]
    held = _STATE_CODE_MAP[protocol.federated_benchmark.held_out_state]
    held_all = by_state(train)[held]

    mean, std = _global_stats(inner_tr, "distributed")
    results = {}
    for lam in LAMBDAS:
        local = LinearHeadClient(held, by_state(inner_tr)[held], ridge_lambda=lam)
        central = LinearHeadClient("ALL", inner_tr, ridge_lambda=lam, feature_mean=mean, feature_std=std)
        w_local = local.fit(local.get_parameters({}), {})[0]
        w_central = central.fit(central.get_parameters({}), {})[0]
        inner_va = held_all[pd.to_datetime(held_all["month"]) >= INNER_CUTOFF - pd.DateOffset(months=3)]
        ev_local = LinearHeadClient(held, inner_va, feature_mean=local.feature_mean, feature_std=local.feature_std)
        ev_central = LinearHeadClient(held, inner_va, feature_mean=mean, feature_std=std)
        keep = np.asarray(_scored_months(inner_va) >= INNER_CUTOFF)
        results[lam] = {
            "local": _wape_on(ev_local, w_local, keep),
            "centralised": _wape_on(ev_central, w_central, keep),
        }
        print(f"lambda={lam:<6} local {results[lam]['local']:.4f}  centralised {results[lam]['centralised']:.4f}")
    return results


def _scored_months(panel: pd.DataFrame) -> pd.Series:
    from ml.forecast.features import build_features
    featured = build_features(panel, Grain.DISTRICT_MONTH, target_col="distributed").dropna(subset=["distributed"])
    return pd.to_datetime(featured["month"]).reset_index(drop=True)


def _wape_on(client: LinearHeadClient, params: list[np.ndarray], keep: np.ndarray) -> float:
    from eval.metrics import wape
    X_aug = np.hstack([client.X, np.ones((len(client.y), 1))])
    pred = X_aug @ params[0]
    return float(wape(np.expm1(client.y[keep]), np.expm1(pred[keep])))


if __name__ == "__main__":
    main()
