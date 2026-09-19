"""AC6: does proactive redistribution reduce stock-outs versus today's
status quo (no lateral transfers between monthly indents)?

Both arms run through eval/replay_sim.py with identical demand, outbreak
shocks, supply delays and leakage. They share a warm-up with no transfers,
then diverge over the frozen synthetic test window (the trailing
`synthetic_benchmark.test_weeks` of the ledger). The solver arm calls the
production proposer every week using only reported history and current
on-hand. The solver's cover_weeks was chosen on the 26 weeks before the
test window (eval/tune_replay.py), never on the test window.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from eval.protocol import load_protocol
from eval.replay_sim import build_world, compare
from eval.run_final import REPORTS_PATH, _git_sha

DEV_WEEKS = 26


def windows(n_weeks: int, test_weeks: int) -> dict[str, tuple[int, int]]:
    test_start = n_weeks - test_weeks
    return {"dev": (test_start - DEV_WEEKS, test_start), "test": (test_start, n_weeks)}


def solver_policy(world, cfg=None):
    from ml.data.facilities import load_facilities
    from ml.optimize.service import propose
    facilities = load_facilities(state="Maharashtra", district="Nashik")
    drug_ids = sorted({d for _, d in world.series})
    return lambda observed, on_hand: propose(facilities, drug_ids, {}, on_hand, cfg=cfg, panel=observed)


def run(window: str = "test", cfg=None, world=None) -> dict:
    protocol = load_protocol()
    world = world or build_world(protocol.generator_seal.seed, protocol.real_benchmark.train_start, protocol.real_benchmark.test_end)
    start, stop = windows(len(world.weeks), protocol.synthetic_benchmark.test_weeks)[window]
    result = compare(world, start, stop, solver_policy(world, cfg))
    return {arm: {k: float(v) for k, v in metrics.items()} for arm, metrics in result.items()}


def main() -> None:
    protocol = load_protocol()
    result = run("test")
    record = {
        "run_id": str(uuid.uuid4()), "git_sha": _git_sha(), "model": "replay_solver_vs_status_quo",
        "grain": "FACILITY_WEEK", "metrics": result,
        "protocol_hash": protocol.generator_seal.content_hash,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(REPORTS_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
