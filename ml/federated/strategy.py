"""FedProx + DP strategy configuration (modular-plan.md §2.13). Returns a
real `flwr.server.strategy.FedProx` instance for its configuration/typing
(the proximal term itself is applied client-side in
ml/federated/client.py's local loss, per FedProx's actual design -- the
server-side role is aggregation). `aggregate()` is the weighted-average
aggregation FedProx performs server-side, exposed as a plain function so
ml/federated/server.py can run rounds without standing up Flower's full
gRPC/Ray simulation transport (see server.py's docstring for why).
"""
from __future__ import annotations

import numpy as np
from flwr.server.strategy import FedProx


def fedprox_dp(mu: float, clip_norm: float, noise_multiplier: float, min_clients: int = 2) -> FedProx:
    return FedProx(
        proximal_mu=mu, fraction_fit=1.0, fraction_evaluate=1.0,
        min_fit_clients=min_clients, min_evaluate_clients=min_clients, min_available_clients=min_clients,
    )


def aggregate(fit_results: list[tuple[list[np.ndarray], int]]) -> list[np.ndarray]:
    """Weighted average of client parameters by num_examples -- this is
    exactly what FedProx's (and FedAvg's) server-side aggregate_fit does;
    exposed directly so it can run without a ClientProxy/gRPC round trip."""
    total_examples = sum(n for _, n in fit_results if n > 0)
    if total_examples == 0:
        return fit_results[0][0]
    n_arrays = len(fit_results[0][0])
    aggregated = []
    for i in range(n_arrays):
        weighted_sum = sum(params[i] * n for params, n in fit_results if n > 0)
        aggregated.append(weighted_sum / total_examples)
    return aggregated
