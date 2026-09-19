"""Logs the local-only / federated / centralised comparison for the
held-out state (modular-plan.md step 39). Uses the validation split only
(never the frozen test window), and appends to the same
eval/reports/runs.jsonl ledger as eval/run_final.py, so every scored run
-- forecasting or federated -- lives in one auditable history.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from eval.protocol import load_protocol
from eval.run_final import REPORTS_PATH, _git_sha
from ml.federated.experiments import compare


def run(reports_path=REPORTS_PATH, rounds: int = 5) -> dict:
    protocol = load_protocol()
    df = compare(rounds=rounds)
    record = {
        "run_id": __import__("uuid").uuid4().hex,
        "git_sha": _git_sha(),
        "model": "federated_linear_head",
        "grain": "DISTRICT_MONTH",
        "metrics": {"arms": df.to_dict(orient="records")},
        "protocol_hash": protocol.generator_seal.content_hash,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    reports_path.parent.mkdir(parents=True, exist_ok=True)
    with open(reports_path, "a") as f:
        f.write(json.dumps(record) + "\n")
    return record


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))
