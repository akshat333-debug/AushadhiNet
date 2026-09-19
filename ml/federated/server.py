"""Runs federated rounds across clients (modular-plan.md §2.13).

Calls each client's `fit`/`evaluate` directly in-process rather than
through Flower's gRPC/Ray-based simulation transport (`flwr.simulation`
needs the `ray` extra, which is heavy and was judged not worth the
dependency weight and startup fragility for what is, underneath, the same
FedProx weighted-averaging math either way -- ml/federated/strategy.py's
`aggregate()` is the real aggregation code, just invoked locally). If
demonstrating actual multi-process/network Flower deployment becomes a
requirement, this is the file to swap for `flwr.simulation.run_simulation`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ml.federated.client import LinearHeadClient
from ml.federated.strategy import aggregate


@dataclass
class GlobalModel:
    parameters: list[np.ndarray]
    loss_history: list[float] = field(default_factory=list)
    rounds_run: int = 0


def run(clients: list[LinearHeadClient], rounds: int) -> GlobalModel:
    if not clients:
        raise ValueError("at least one client is required")
    parameters = clients[0].get_parameters({})

    loss_history = []
    for _ in range(rounds):
        fit_results = []
        round_losses = []
        for client in clients:
            new_params, n, metrics = client.fit(parameters, {})
            if n > 0:
                fit_results.append((new_params, n))
                round_losses.append(metrics.get("loss", float("nan")))
        if fit_results:
            parameters = aggregate(fit_results)
        loss_history.append(float(np.nanmean(round_losses)) if round_losses else float("nan"))

    return GlobalModel(parameters=parameters, loss_history=loss_history, rounds_run=rounds)
