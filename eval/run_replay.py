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
    return {arm: {k: float(v) for k, v in metrics.items() if k != "per_series"} for arm, metrics in result.items()}


def counts_policy(world, cfg):
    """The live chain end to end: demand from the facility's own weekly counts through the same
    estimator the app runs (ml/forecast/reported_use.py), with the same knowledge the app has.
    It learns each closing count and the transfers it made itself; deliveries from the state's
    supply are unknown to it, exactly as in the app, so a count that rose gives no reading.
    Only past counts are used: the count of week i-1 is read at the start of week i."""
    from ml.data.facilities import load_facilities
    from ml.forecast.reported_use import UseEstimator
    from ml.optimize.service import propose
    facilities = load_facilities(state="Maharashtra", district="Nashik")
    drug_ids = sorted({d for _, d in world.series})
    est, moved = UseEstimator(), {}

    def policy(observed, on_hand):
        when = None
        if not observed.empty:
            last = observed[observed["week"] == observed["week"].max()]
            when = last["week"].iloc[0].date()
            day = last["week"].iloc[0].value / 86_400e9 + 7  # the close of that week
            for f, d, close in zip(last["facility_id"], last["drug_id"], last["on_hand_close"]):
                est.observe((f, d), day, float(close), moved.pop((f, d), 0.0))
        use = {k: (r, when) for k, r in est.rates.items()}
        orders = propose(facilities, drug_ids, {}, on_hand, cfg=cfg, panel=observed, recent_use=use)
        for o in orders:
            moved[(o.from_facility_id, o.drug_id)] = moved.get((o.from_facility_id, o.drug_id), 0.0) - o.quantity
            moved[(o.to_facility_id, o.drug_id)] = moved.get((o.to_facility_id, o.drug_id), 0.0) + o.quantity
        return orders
    return policy


def breakdown() -> dict:
    """Status quo, the deployed policy on ledger demand, and the deployed policy on demand read
    from counts, over the same frozen test window and the same hidden events (common random
    numbers). The objective stays what it was: fewer facility-weeks with unmet demand, reported
    beside unmet units, fill rate and transport, per medicine and per facility."""
    import copy
    import numpy as np
    from backend.runtime import MAX_SOURCES, MIN_SHIPMENT
    from eval.replay_sim import initial_state, run_weeks
    from ml.optimize.constraints import SolverConfig
    protocol = load_protocol()
    cfg = SolverConfig(min_transfer_units=MIN_SHIPMENT, max_sources=MAX_SOURCES)
    world = build_world(protocol.generator_seal.seed, protocol.real_benchmark.train_start, protocol.real_benchmark.test_end)
    start, stop = windows(len(world.weeks), protocol.synthetic_benchmark.test_weeks)["test"]
    warm = initial_state(world)
    run_weeks(world, warm, 0, start)
    arms = {"status_quo": None, "ledger_demand": solver_policy(world, cfg), "count_demand": counts_policy(world, cfg)}
    raw = {name: run_weeks(world, copy.deepcopy(warm), start, stop, policy) for name, policy in arms.items()}

    facility = np.array([f for f, _ in world.series])
    drug = np.array([d for _, d in world.series])
    out = {"window_weeks": stop - start, "arms": {}, "by_medicine": {}, "by_facility": {}}
    base = raw["status_quo"]["per_series"]
    for name, r in raw.items():
        per = r["per_series"]
        out["arms"][name] = {**{k: float(v) for k, v in r.items() if k != "per_series"},
                             "units_per_transfer": r["units_moved"] / r["transfers"] if r["transfers"] else 0.0,
                             "drive_minutes_per_unit_moved": r["drive_minutes"] / r["units_moved"] if r["units_moved"] else 0.0}
        meds = {}
        for d in sorted(set(drug)):
            m = drug == d
            meds[d] = {"stockout_weeks": int(per["stockout_weeks"][m].sum()), "unmet_units": round(float(per["unmet"][m].sum())),
                       "fill_rate": round(1 - float(per["unmet"][m].sum()) / max(float(per["wanted"][m].sum()), 1e-9), 4),
                       "units_moved": round(float(per["received"][m].sum()))}
        out["by_medicine"][name] = meds
        if name != "status_quo":
            by_fac = {f: (int(per["stockout_weeks"][facility == f].sum() - base["stockout_weeks"][facility == f].sum()),
                          float(per["unmet"][facility == f].sum() - base["unmet"][facility == f].sum()),
                          int(per["trips_out"][facility == f].sum()))
                      for f in sorted(set(facility))}
            deltas = np.array([v[0] for v in by_fac.values()])
            out["by_facility"][name] = {
                "facilities_fewer_stockout_weeks": int((deltas < 0).sum()), "facilities_more_stockout_weeks": int((deltas > 0).sum()),
                "facilities_unchanged": int((deltas == 0).sum()),
                "facilities_more_unmet_units": int(sum(v[1] > 0.5 for v in by_fac.values())),
                "worst_10_by_added_unmet_units": sorted(([f, round(v[1]), v[0], v[2]] for f, v in by_fac.items()), key=lambda x: -x[1])[:10],
                "busiest_10_donors_by_trips": sorted(([f, v[2], round(v[1])] for f, v in by_fac.items()), key=lambda x: -x[1])[:10],
            }
    return out


def main() -> None:
    """`--live`: the policy the app deploys (backend/runtime.py: no shipment under MIN_SHIPMENT
    units, at most MAX_SOURCES donors per recipient and medicine), recorded as its own run."""
    import sys
    from ml.optimize.constraints import SolverConfig
    if "--breakdown" in sys.argv[1:]:
        result = breakdown()
        path = REPORTS_PATH.parent / "replay_breakdown.json"
        path.write_text(json.dumps(result, indent=1))
        with open(REPORTS_PATH, "a") as f:
            f.write(json.dumps({"run_id": str(uuid.uuid4()), "git_sha": _git_sha(), "model": "replay_deployed_policy_ledger_vs_count_demand",
                                "grain": "FACILITY_WEEK", "metrics": result["arms"], "protocol_hash": load_protocol().generator_seal.content_hash,
                                "timestamp": datetime.now(timezone.utc).isoformat(), "detail": str(path.name)}) + "\n")
        print(json.dumps(result["arms"], indent=2))
        return
    live = "--live" in sys.argv[1:]
    cfg = None
    if live:
        from backend.runtime import MAX_SOURCES, MIN_SHIPMENT
        cfg = SolverConfig(min_transfer_units=MIN_SHIPMENT, max_sources=MAX_SOURCES)
    protocol = load_protocol()
    result = run("test", cfg)
    record = {
        "run_id": str(uuid.uuid4()), "git_sha": _git_sha(),
        "model": "replay_solver_vs_status_quo" + ("_live_policy" if live else ""),
        "grain": "FACILITY_WEEK", "metrics": result,
        "protocol_hash": protocol.generator_seal.content_hash,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(REPORTS_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
