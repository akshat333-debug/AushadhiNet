"""One state's federated client as its own OS process (`python -m ml.federated.node`). It reads
only its own state's HMIS files and exchanges only aggregates with the coordinator
(ml/federated/demo.py), through files in a shared directory standing in for the network:

  stats     -> <state>.stats.npz   row count, feature sums and sums of squares
  fit       <- global.npz          shared feature scale and the current global weights
            -> <state>.update.npz  this state's FedProx update and its row count
  features  -> <state>.latest.json latest validation month, features only (served by the API)

shortcut: a shared directory, not Flower's gRPC transport; the messages are the same, and a
deployment puts each node in its state's own GCP project.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd

from backend.domain import Grain

FILE_CODE = {"MH": "mah", "HR": "har", "AS": "as", "ML": "meg"}  # HMIS filename codes (ml/data/hmis_m19.py)
TARGET = "distributed"


def own_data(state: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """This state's training and validation months, loaded from its own files only."""
    from eval.protocol import load_protocol
    from eval.splits import for_grain
    from ml.data.panel import build
    panel = build(Grain.DISTRICT_MONTH, states=[FILE_CODE[state]])
    split = for_grain(Grain.DISTRICT_MONTH, load_protocol())
    return panel[split.train_mask(panel)], panel[split.val_mask(panel)]


def _latest_features(val: pd.DataFrame, mean: np.ndarray, std: np.ndarray) -> dict:
    """The last validation month per district and medicine: standardised features and the
    actual units, so the API can show the model's estimate beside what was distributed."""
    from ml.forecast.features import build_features, feature_columns
    featured = build_features(val, Grain.DISTRICT_MONTH, target_col=TARGET).dropna(subset=[TARGET])
    last = featured[featured["month"] == featured["month"].max()]
    cols = list(feature_columns(featured, TARGET))
    X = (np.log1p(last[cols].fillna(0.0).clip(lower=0).to_numpy(dtype=float)) - mean) / std
    return {"month": str(pd.Timestamp(last["month"].max()).date()), "rows": [
        {"district_id": d, "drug": n, "actual": float(a), "x": [round(float(v), 6) for v in x]}
        for d, n, a, x in zip(last["district_id"], last["drug_name"], last[TARGET], X)]}


def main(state: str, phase: str, workdir: pathlib.Path) -> None:
    from ml.federated.client import LinearHeadClient, _design_matrix
    train, val = own_data(state)
    if phase == "stats":
        X, _, _ = _design_matrix(train, TARGET)
        np.savez(workdir / f"{state}.stats.npz", n=len(X), total=X.sum(axis=0), squares=(X ** 2).sum(axis=0))
    elif phase == "fit":
        g = np.load(workdir / "global.npz")
        client = LinearHeadClient(state, train, proximal_mu=0.1, feature_mean=g["mean"], feature_std=g["std"])
        (w,), n, _ = client.fit([g["w"]], {})
        np.savez(workdir / f"{state}.update.npz", w=w, n=n)
    elif phase == "features":
        g = np.load(workdir / "global.npz")
        (workdir / f"{state}.latest.json").write_text(json.dumps(_latest_features(val, g["mean"], g["std"])))
    else:
        raise SystemExit(f"unknown phase {phase}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: python -m ml.federated.node <MH|HR|AS|ML> <stats|fit|features> <workdir>")
    main(sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3]))
