"""DoD test for eval/run_final.py (step 21)."""
from __future__ import annotations

import json

from eval.run_final import append_run


def test_append_writes_exactly_one_jsonl_line(tmp_path):
    path = tmp_path / "runs.jsonl"
    append_run("seasonal_naive", reports_path=path)
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["model"] == "seasonal_naive"
    assert "git_sha" in record
    assert "protocol_hash" in record
    assert "metrics" in record and "wape" in record["metrics"]


def test_second_run_appends_never_overwrites(tmp_path):
    path = tmp_path / "runs.jsonl"
    append_run("seasonal_naive", reports_path=path)
    append_run("lgbm", reports_path=path)
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 2
    models = [json.loads(line)["model"] for line in lines]
    assert models == ["seasonal_naive", "lgbm"]


def test_each_run_has_a_unique_run_id(tmp_path):
    path = tmp_path / "runs.jsonl"
    append_run("seasonal_naive", reports_path=path)
    append_run("seasonal_naive", reports_path=path)
    lines = path.read_text().strip().splitlines()
    run_ids = [json.loads(line)["run_id"] for line in lines]
    assert len(set(run_ids)) == 2
