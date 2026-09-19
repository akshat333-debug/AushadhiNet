"""Counterfactual stock-ledger simulator for the AC6 replay.

Re-runs the sealed generator's inventory dynamics (order-up-to-cover,
FEFO, leakage, expiry, outbreak shocks, supply delays) for every facility
x drug, with one change: every hidden event is drawn up front from a fixed
seed, so two policies see identical demand, shocks and delays (common
random numbers). The ledger's own RNG stream is not reusable for this --
its delay draws depend on stock levels, so a counterfactual would shift
every later draw.

Scoring uses true (shocked) demand, which only this module knows. The
policy under test sees only what a facility reports: noisy dispensed
counts and closing stock for past weeks, plus current on-hand.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

from ml.generator import _iso_weeks
from ml.generator.anchor import scale_to_anchor
from ml.generator.cli import _build_anchors, _m19_drug_subset
from ml.generator.demand import base_shape
from ml.generator.params import GeneratorParams

HISTORY_WEEKS = 8  # what the naive forecaster reads (last value + 8-week spread)


@dataclass
class World:
    series: list[tuple[str, str]]
    weeks: list[pd.Timestamp]
    target: np.ndarray        # n_series x n_weeks, pre-shock demand
    wanted: np.ndarray        # n_series x n_weeks, true demand after outbreak shocks
    noise: np.ndarray         # reporting noise on dispensed
    delayed: np.ndarray       # supply delay draw for an order placed that week
    params: GeneratorParams


@dataclass
class State:
    batches: list[list[list[float]]]      # per series: [[expiry_week, qty], ...]
    pipeline: list[dict[int, float]]
    reported: list[np.ndarray] = field(default_factory=list)   # rolling history of reported dispensed
    closing: list[np.ndarray] = field(default_factory=list)    # rolling history of on_hand_close
    history_weeks: list[pd.Timestamp] = field(default_factory=list)


def build_world(seed: int, start, end, event_seed_offset: int = 7) -> World:
    from ml.data.facilities import load_facilities
    params = GeneratorParams(seed=seed)
    facilities = load_facilities(state="Maharashtra", district="Nashik")
    drugs, name_to_id = _m19_drug_subset()
    weeks = _iso_weeks(start, end)
    shape = base_shape(facilities, drugs, weeks, params)
    targets = scale_to_anchor(shape, {f.facility_id: f.district_id for f in facilities}, _build_anchors("Nashik", name_to_id))

    pivot = targets.pivot_table(index=["facility_id", "drug_id"], columns="week", values="target_dispense", fill_value=0.0)
    pivot = pivot.reindex(columns=weeks, fill_value=0.0)
    target = pivot.to_numpy(dtype=float)

    rng = np.random.default_rng(seed + event_seed_offset)
    shock = rng.random(target.shape) < params.outbreak_shock_prob
    wanted = np.where(shock & (target > 0), target * params.outbreak_shock_multiplier, target)
    noise = rng.normal(0.0, params.reporting_noise_std, target.shape)
    delayed = rng.random(target.shape) < params.supply_delay_prob
    return World(list(pivot.index), weeks, target, wanted, noise, delayed, params)


def initial_state(world: World) -> State:
    p = world.params
    batches, pipeline = [], []
    for s in range(len(world.series)):
        avg = float(world.target[s, :8].mean())
        batches.append([[float(p.default_shelf_life_weeks), avg * p.reorder_buffer_weeks]] if avg > 0 else [])
        pipeline.append({})
    return State(batches, pipeline)


def _on_hand(batches) -> float:
    return sum(q for _, q in batches)


def _take_fefo(batches, qty: float) -> list[list[float]]:
    """Removes qty from the earliest-expiring batches; returns what was taken."""
    taken, remaining = [], qty
    batches.sort(key=lambda b: b[0])
    for b in batches:
        if remaining <= 1e-9:
            break
        take = min(b[1], remaining)
        b[1] -= take
        remaining -= take
        taken.append([b[0], take])
    batches[:] = [b for b in batches if b[1] > 1e-9]
    return taken


def observed_history(world: World, state: State) -> pd.DataFrame:
    """What the policy may see: reported dispensed and closing stock for past weeks."""
    if not state.history_weeks:
        return pd.DataFrame(columns=["facility_id", "drug_id", "week", "dispensed", "on_hand_close"])
    n, h = len(world.series), len(state.history_weeks)
    fac = np.array([f for f, _ in world.series])
    drug = np.array([d for _, d in world.series])
    return pd.DataFrame({
        "facility_id": np.tile(fac, h), "drug_id": np.tile(drug, h),
        "week": np.repeat(np.array(state.history_weeks, dtype="datetime64[ns]"), n),
        "dispensed": np.concatenate(state.reported), "on_hand_close": np.concatenate(state.closing),
    })


Policy = Callable[[pd.DataFrame, dict[tuple[str, str], float]], list]


def run_weeks(world: World, state: State, start: int, stop: int, policy: Policy | None = None) -> dict:
    """Advances `state` through weeks [start, stop). `policy`, if given, is called at the start
    of each week with the observed history and current on-hand, and returns TransferOrders."""
    p = world.params
    index = {key: s for s, key in enumerate(world.series)}
    n = len(world.series)
    totals = {"wanted_units": 0.0, "unmet_units": 0.0, "stockout_weeks": 0, "expired_units": 0.0,
              "transfers": 0, "units_moved": 0.0, "drive_minutes": 0.0}

    for i in range(start, stop):
        for s in range(n):
            arrived = state.pipeline[s].pop(i, 0.0)
            if arrived > 0:
                state.batches[s].append([float(i + p.default_shelf_life_weeks), arrived])

        if policy is not None:
            on_hand = {world.series[s]: _on_hand(state.batches[s]) for s in range(n)}
            for order in policy(observed_history(world, state), on_hand):
                src, dst = index.get((order.from_facility_id, order.drug_id)), index.get((order.to_facility_id, order.drug_id))
                if src is None or dst is None:
                    continue
                moved = _take_fefo(state.batches[src], float(order.quantity))
                qty = sum(q for _, q in moved)
                state.batches[dst].extend(moved)
                totals["transfers"] += 1
                totals["units_moved"] += qty
                totals["drive_minutes"] += order.drive_minutes

        reported = np.zeros(n)
        closing = np.zeros(n)
        for s in range(n):
            b = state.batches[s]
            wanted = world.wanted[s, i]
            dispensed = min(wanted, _on_hand(b))
            _take_fefo(b, dispensed)
            _take_fefo(b, _on_hand(b) * p.leakage_rate)
            expired = sum(q for e, q in b if e <= i)
            b[:] = [x for x in b if x[0] > i]
            close = _on_hand(b)

            unmet = wanted - dispensed
            totals["wanted_units"] += wanted
            totals["unmet_units"] += unmet
            totals["stockout_weeks"] += int(unmet > 0.5)
            totals["expired_units"] += expired
            reported[s] = max(0.0, dispensed * (1.0 + world.noise[s, i]))
            closing[s] = close

            avg = float(world.target[s, max(0, i - 7): i + 1].mean())
            order_qty = max(0.0, avg * p.reorder_buffer_weeks - close - sum(state.pipeline[s].values()))
            if order_qty > 0:
                arrival = i + p.lead_time_weeks
                if world.delayed[s, i]:
                    arrival += p.supply_delay_extra_weeks
                    order_qty *= 0.5
                if arrival < len(world.weeks):
                    state.pipeline[s][arrival] = state.pipeline[s].get(arrival, 0.0) + order_qty

        state.reported = (state.reported + [reported])[-HISTORY_WEEKS:]
        state.closing = (state.closing + [closing])[-HISTORY_WEEKS:]
        state.history_weeks = (state.history_weeks + [world.weeks[i]])[-HISTORY_WEEKS:]

    totals["fill_rate"] = 1.0 - totals["unmet_units"] / totals["wanted_units"] if totals["wanted_units"] else 1.0
    return totals


def compare(world: World, window_start: int, window_stop: int, policy: Policy) -> dict:
    """Shared warm-up to window_start with no transfers, then both arms over the window."""
    state = initial_state(world)
    run_weeks(world, state, 0, window_start)
    status_quo_state = copy.deepcopy(state)
    return {
        "status_quo": run_weeks(world, status_quo_state, window_start, window_stop),
        "solver": run_weeks(world, state, window_start, window_stop, policy),
    }
