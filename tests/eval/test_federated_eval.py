"""DoD test for ml/federated/experiments.py + eval/run_federated_eval.py
(step 39)."""
from __future__ import annotations

import json

from ml.federated.experiments import compare


def test_all_three_arms_reported_for_meghalaya():
    df = compare(rounds=3)
    assert set(df["arm"]) == {"local_only", "federated", "centralised"}
    assert (df["state"] == "ML").all()
    assert (df["wape"] >= 0).all()


def test_run_is_logged_to_runs_jsonl(tmp_path):
    from eval.run_federated_eval import run

    path = tmp_path / "runs.jsonl"
    record = run(reports_path=path, rounds=2)
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 1
    logged = json.loads(lines[0])
    assert logged["model"] == "federated_linear_head"
    assert logged["run_id"] == record["run_id"]
    assert len(logged["metrics"]["arms"]) == 3
    assert "protocol_hash" in logged and "git_sha" in logged


def test_second_federated_run_appends():
    from eval.run_federated_eval import run
    import tempfile
    import pathlib

    path = pathlib.Path(tempfile.mkdtemp()) / "runs.jsonl"
    run(reports_path=path, rounds=2)
    run(reports_path=path, rounds=2)
    assert len(path.read_text().strip().splitlines()) == 2
