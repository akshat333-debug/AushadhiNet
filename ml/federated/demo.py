"""Connected federation demo (`python -m ml.federated.demo`): two state nodes run as separate
processes (ml/federated/node.py), the coordinator aggregates what they send, and the API
serves the resulting model (backend/api/public.py, /public/federated). The coordinator never
opens a state's data; it sees row counts, feature sums and model weights only.

  1. each node sends n, sums, sums of squares -> one shared feature scale
  2. one FedProx round: each node fits from the shared weights, the coordinator averages
     the updates by row count (ml/federated/strategy.py, the code the experiment uses)
  3. the data-poor node sends its latest month's features for serving

Writes backend/federated/model.npz and <state>.latest.json. Same caveats as the experiment
(ml/federated/experiments.py): no differential privacy (noise 0), and its validation accuracy
roughly ties a local-only model; what this shows is the mechanism, end to end.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

import numpy as np

from ml.federated.strategy import aggregate

STATES = ("MH", "ML")  # data-rich Maharashtra and data-poor Meghalaya (eval/protocol.lock)
OUT = pathlib.Path(__file__).resolve().parents[2] / "backend" / "federated"


def _run_nodes(phase: str, workdir: pathlib.Path, states=STATES) -> None:
    procs = [subprocess.Popen([sys.executable, "-m", "ml.federated.node", s, phase, str(workdir)]) for s in states]
    if any(p.wait() for p in procs):
        raise SystemExit(f"a node failed in phase {phase}")


def main(rounds: int = 1) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        workdir = pathlib.Path(tmp)
        _run_nodes("stats", workdir)
        stats = [np.load(workdir / f"{s}.stats.npz") for s in STATES]
        n = sum(int(s["n"]) for s in stats)
        mean = sum(s["total"] for s in stats) / n
        std = np.sqrt(np.maximum(sum(s["squares"] for s in stats) / n - mean ** 2, 0.0))
        std = np.where(std > 1e-9, std, 1.0)
        w = np.zeros(len(mean) + 1)
        for _ in range(rounds):
            np.savez(workdir / "global.npz", mean=mean, std=std, w=w)
            _run_nodes("fit", workdir)
            updates = [np.load(workdir / f"{s}.update.npz") for s in STATES]
            (w,) = aggregate([([u["w"]], int(u["n"])) for u in updates])
        np.savez(workdir / "global.npz", mean=mean, std=std, w=w)
        _run_nodes("features", workdir, states=("ML",))
        OUT.mkdir(exist_ok=True)
        card = {"states": list(STATES), "training_rows": {s: int(st["n"]) for s, st in zip(STATES, stats)}, "rounds": rounds,
                "trained_at": datetime.now(timezone.utc).isoformat(), "target": "units distributed per district, medicine and month"}
        columns = [list(s["columns"]) for s in stats]
        assert all(c == columns[0] for c in columns), "states must share one feature schema"
        # Weights with the preprocessing that makes them usable on fresh inputs: feature names
        # (log1p of each, missing as 0) and the shared scale.
        np.savez(OUT / "model.npz", w=w, mean=mean, std=std, columns=np.array(columns[0]), card=json.dumps(card))
        (OUT / "ML.latest.json").write_text((workdir / "ML.latest.json").read_text())
    return card


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
