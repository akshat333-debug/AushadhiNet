"""The connected federation demo: two state processes, aggregation, and the API serving the model."""
from __future__ import annotations

import json

import numpy as np
from fastapi.testclient import TestClient

from backend.app import create_app


def test_two_state_processes_produce_one_aggregated_model(tmp_path, monkeypatch):
    from ml.federated import demo
    monkeypatch.setattr(demo, "OUT", tmp_path)
    card = demo.main()
    assert card["states"] == ["MH", "ML"] and all(n > 0 for n in card["training_rows"].values())
    model = np.load(tmp_path / "model.npz")
    assert json.loads(str(model["card"]))["trained_at"] == card["trained_at"]
    assert len(model["w"]) == len(json.loads((tmp_path / "ML.latest.json").read_text())["rows"][0]["x"]) + 1


def test_the_api_serves_the_committed_federated_model():
    served = TestClient(create_app()).get("/public/federated").json()
    assert served["states"] == ["MH", "ML"] and served["rows"] and 0 <= served["wape"] < 5
