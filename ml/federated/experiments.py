"""Compares local-only vs federated vs centralised training for the
data-poor state (modular-plan.md §2.13, project.md's federation
demonstration). Scored on validation only (never the frozen test window
-- architecture.md §5 reserves that for eval/run_final.py alone).

Federated and centralised arms share ONE set of feature-normalisation
statistics across every client and the evaluation, since a shared weight
vector is only meaningful in a shared feature space (see client.py). Those
statistics are aggregated from each state's row count, sums and sums of
squares, so no state's rows leave it. The local-only arm uses the data-poor
state's own TRAINING statistics, for fitting and for scoring validation.

What this is: an in-process simulation of federated training (Flower's
client API, FedProx), not a deployed multi-project federation; the data-poor
state takes part in training (a few-shot participating state, not an unseen
one); and the scored runs use noise multiplier 0, so they carry no
differential-privacy guarantee.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from backend.domain import Grain

from eval.protocol import load_protocol
from eval.splits import for_grain
from ml.federated.client import LinearHeadClient, _design_matrix
from ml.federated.partition import by_state
from ml.federated.server import run as run_federated

_STATE_CODE_MAP = {"maharashtra": "MH", "haryana": "HR", "assam": "AS", "meghalaya": "ML"}


def _stats(parts: list[pd.DataFrame], target_col: str) -> tuple[np.ndarray, np.ndarray]:
    """Mean and std from each part's n, sum and sum of squares: what a state can share without
    sharing rows. Equal to computing them on the pooled rows (population std)."""
    n, total, squares = 0, 0.0, 0.0
    for df in parts:
        X_raw, _, _ = _design_matrix(df, target_col)
        if X_raw.size:
            n, total, squares = n + len(X_raw), total + X_raw.sum(axis=0), squares + (X_raw ** 2).sum(axis=0)
    if not n:
        return np.zeros(0), np.ones(0)
    mean = total / n
    std = np.sqrt(np.maximum(squares / n - mean ** 2, 0.0))
    return mean, np.where(std > 1e-9, std, 1.0)


def compare(panel: pd.DataFrame | None = None, rounds: int = 5, target_col: str = "distributed") -> pd.DataFrame:
    from ml.data.panel import build as build_panel

    protocol = load_protocol()
    panel = panel if panel is not None else build_panel(Grain.DISTRICT_MONTH)
    split = for_grain(Grain.DISTRICT_MONTH, protocol)
    train = panel[split.train_mask(panel)]
    val = panel[split.val_mask(panel)]

    held_out_code = _STATE_CODE_MAP[protocol.federated_benchmark.held_out_state]
    train_parts = by_state(train)
    val_parts = by_state(val)
    if held_out_code not in val_parts:
        return pd.DataFrame(columns=["arm", "state", "wape", "n"])

    global_mean, global_std = _stats(list(train_parts.values()), target_col)
    local_mean, local_std = _stats([train_parts[held_out_code]], target_col)
    rows = []

    # Arm 1: local-only -- the data-poor state trains on its own data, and validation is scaled
    # with its training statistics (rescaling with validation's own was a leak, fixed 2026-10-26).
    local_client = LinearHeadClient(held_out_code, train_parts[held_out_code], feature_mean=local_mean, feature_std=local_std)
    local_params, _, _ = local_client.fit(local_client.get_parameters({}), {})
    local_eval = LinearHeadClient(held_out_code, val_parts[held_out_code], feature_mean=local_mean, feature_std=local_std)
    wape_local, n, _ = local_eval.evaluate(local_params, {})
    rows.append({"arm": "local_only", "state": held_out_code, "wape": wape_local, "n": n})

    # Arm 2: federated -- every state trains (held-out state included as
    # a client) under the SAME global feature scale, aggregated via FedProx.
    fed_clients = [
        LinearHeadClient(state, df, proximal_mu=0.1, feature_mean=global_mean, feature_std=global_std)
        for state, df in train_parts.items()
    ]
    global_model = run_federated(fed_clients, rounds=rounds)
    fed_eval = LinearHeadClient(held_out_code, val_parts[held_out_code], feature_mean=global_mean, feature_std=global_std)
    wape_fed, n, _ = fed_eval.evaluate(global_model.parameters, {})
    rows.append({"arm": "federated", "state": held_out_code, "wape": wape_fed, "n": n})

    # Arm 3: centralised -- one model trained on all states' pooled raw
    # data under the same global scale (the upper bound federation
    # approaches without ever pooling raw data).
    centralised_client = LinearHeadClient("ALL", train, feature_mean=global_mean, feature_std=global_std)
    centralised_params, _, _ = centralised_client.fit(centralised_client.get_parameters({}), {})
    central_eval = LinearHeadClient(held_out_code, val_parts[held_out_code], feature_mean=global_mean, feature_std=global_std)
    wape_central, n, _ = central_eval.evaluate(centralised_params, {})
    rows.append({"arm": "centralised", "state": held_out_code, "wape": wape_central, "n": n})

    return pd.DataFrame(rows)
