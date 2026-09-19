"""The stock-ledger simulation: turns a target weekly dispense series into
an actual facility x drug x week inventory ledger with opening balance,
receipts, dispensed, unusable (expiry + leakage) and closing stock, using
an order-up-to-cover policy and FEFO (first-expiry-first-out) batch
consumption (modular-plan.md §2.8, DoD in tests/ml/generator/test_generator.py).

Hidden drivers live here and ONLY here: outbreak shocks (temporarily
inflate what a facility tries to dispense), supply delays (a scheduled
delivery arrives late or short), and leakage (silent stock loss). None of
these are written to any column a forecaster could key on -- the model
only ever sees the resulting on_hand/received/dispensed/unusable numbers,
never the shock/delay/leakage flags themselves. That is the mechanism
behind data/README.md §6.2's "hidden drivers" rule and is exactly what
tests/test_isolation.py enforces at the import level.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ml.generator.params import GeneratorParams


@dataclass
class _Batch:
    batch_no: str
    qty: float
    expiry_week_index: int


@dataclass
class _FacilityDrugState:
    batches: list[_Batch] = field(default_factory=list)
    pipeline: dict[int, float] = field(default_factory=dict)  # arrival_week_index -> qty
    next_batch_seq: int = 0

    def on_hand(self) -> float:
        return sum(b.qty for b in self.batches)


def simulate_ledger(
    target_dispense: pd.DataFrame,  # facility_id, drug_id, week, target_dispense
    weeks: list[pd.Timestamp],
    params: GeneratorParams,
    shelf_life_weeks: dict[str, int] | None = None,
) -> pd.DataFrame:
    """Returns one row per facility x drug x week: on_hand_open, received,
    dispensed, unusable, on_hand_close. Deterministic given params.seed."""
    rng = np.random.default_rng(params.seed + 1)  # offset from demand.py's rng stream
    shelf_life_weeks = shelf_life_weeks or {}
    week_index = {w: i for i, w in enumerate(weeks)}

    rows = []
    for (facility_id, drug_id), group in target_dispense.groupby(["facility_id", "drug_id"], sort=False):
        series = group.set_index("week")["target_dispense"].reindex(weeks, fill_value=0.0)
        recent = series.iloc[:8]
        avg_initial_demand = float(recent.mean()) if len(recent) else 0.0
        life = shelf_life_weeks.get(drug_id, params.default_shelf_life_weeks)

        state = _FacilityDrugState()
        if avg_initial_demand > 0:
            state.batches.append(_Batch(
                batch_no=f"{facility_id}:{drug_id}:seed", qty=avg_initial_demand * params.reorder_buffer_weeks,
                expiry_week_index=life,
            ))

        for i, week in enumerate(weeks):
            on_hand_open = state.on_hand()

            received = state.pipeline.pop(i, 0.0)
            if received > 0:
                state.next_batch_seq += 1
                state.batches.append(_Batch(
                    batch_no=f"{facility_id}:{drug_id}:{state.next_batch_seq}",
                    qty=received, expiry_week_index=i + life,
                ))

            # hidden driver: outbreak shock inflates what the facility tries to dispense
            wanted = float(series.iloc[i])
            if wanted > 0 and rng.random() < params.outbreak_shock_prob:
                wanted *= params.outbreak_shock_multiplier

            available_after_receipt = state.on_hand()
            dispensed = min(wanted, available_after_receipt)
            _consume_fefo(state, dispensed)

            # hidden driver: silent leakage, a fraction of whatever remains
            remaining = state.on_hand()
            leaked = remaining * params.leakage_rate
            _consume_fefo(state, leaked)

            # expiry: any batch whose shelf life has lapsed this week is unusable
            expired = 0.0
            still_good = []
            for b in state.batches:
                if b.expiry_week_index <= i:
                    expired += b.qty
                else:
                    still_good.append(b)
            state.batches = still_good
            unusable = expired + leaked

            on_hand_close = state.on_hand()

            # reporting noise: what gets *recorded* as dispensed differs
            # slightly from what actually left the shelf (a real ANM's
            # register rarely matches the count to the unit)
            reported_dispensed = max(0.0, dispensed * (1.0 + rng.normal(0.0, params.reporting_noise_std)))

            rows.append({
                "facility_id": facility_id, "drug_id": drug_id, "week": week,
                "on_hand_open": on_hand_open, "received": received,
                "dispensed": reported_dispensed, "unusable": unusable,
                "on_hand_close": on_hand_close,
            })

            # order-up-to-cover policy: review weekly, order enough to
            # bring pipeline + on-hand up to reorder_buffer_weeks of the
            # recent average demand, arriving after lead_time_weeks
            if (i % params.review_period_weeks) == 0:
                recent_window = series.iloc[max(0, i - 7): i + 1]
                avg_demand = float(recent_window.mean()) if len(recent_window) else 0.0
                pipeline_qty = sum(state.pipeline.values())
                desired = avg_demand * params.reorder_buffer_weeks
                order_qty = max(0.0, desired - on_hand_close - pipeline_qty)
                if order_qty > 0:
                    arrival = i + params.lead_time_weeks
                    # hidden driver: supply delay, order arrives later and/or short
                    if rng.random() < params.supply_delay_prob:
                        arrival += params.supply_delay_extra_weeks
                        order_qty *= 0.5
                    if arrival < len(weeks):
                        state.pipeline[arrival] = state.pipeline.get(arrival, 0.0) + order_qty

    return pd.DataFrame(rows)


def _consume_fefo(state: _FacilityDrugState, qty: float) -> None:
    """Consume `qty` from the earliest-expiring batches first, mutating
    state.batches in place. Never drives a batch below zero."""
    remaining = qty
    state.batches.sort(key=lambda b: b.expiry_week_index)
    for b in state.batches:
        if remaining <= 0:
            break
        take = min(b.qty, remaining)
        b.qty -= take
        remaining -= take
    state.batches = [b for b in state.batches if b.qty > 1e-9]
