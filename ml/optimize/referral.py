"""Patient referral to a nearby facility with free beds (modular-plan.md
§2.12). A simpler greedy assignment than the drug/staff solvers: referrals
are urgent and typically one-off, so nearest-feasible-bed is the
appropriate policy rather than a global cost optimum.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pandas as pd

from backend.domain import OrderKind, OrderStatus, TransferOrder

from ml.optimize.constraints import SolverConfig


def solve(
    bed_pressure: pd.DataFrame,  # facility_id, patients_to_refer (int)
    free_beds: pd.DataFrame,     # facility_id, free_beds (int)
    drive: "list[list[float]]",
    facility_order: list[str],
    cfg: SolverConfig,
) -> tuple[list[TransferOrder], str | None]:
    if bed_pressure.empty or free_beds.empty:
        return [], "no bed pressure or no free-bed capacity supplied"

    idx_of = {fid: i for i, fid in enumerate(facility_order)}
    remaining_beds = dict(zip(free_beds["facility_id"], free_beds["free_beds"]))
    orders: list[TransferOrder] = []
    unmet = 0

    for _, prow in bed_pressure.iterrows():
        source = prow["facility_id"]
        need = int(prow["patients_to_refer"])
        s_idx = idx_of.get(source)
        if s_idx is None or need <= 0:
            continue

        candidates = []
        for dest, beds in remaining_beds.items():
            if dest == source or beds <= 0:
                continue
            d_idx = idx_of.get(dest)
            if d_idx is None:
                continue
            minutes = drive[s_idx][d_idx]
            if minutes <= cfg.max_drive_minutes:
                candidates.append((minutes, dest, beds))
        candidates.sort(key=lambda c: c[0])  # nearest first

        for minutes, dest, beds in candidates:
            if need <= 0:
                break
            take = min(need, beds, remaining_beds[dest])
            if take <= 0:
                continue
            remaining_beds[dest] -= take
            need -= take
            orders.append(TransferOrder(
                order_id=str(uuid.uuid4()), kind=OrderKind.REFERRAL,
                from_facility_id=source, to_facility_id=dest,
                patient_count=take, drive_minutes=minutes,
                rationale="bed-pressure referral to nearest facility with capacity",
                status=OrderStatus.DRAFT, created_at=datetime.now(timezone.utc), created_by="solver",
            ))
        unmet += need

    if orders:
        return orders, None
    return [], "no drive-time-feasible facility with free beds"
