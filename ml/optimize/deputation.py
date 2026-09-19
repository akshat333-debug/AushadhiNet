"""Staff deputation via CP-SAT (modular-plan.md §2.12): temporarily
assigning available staff from a surplus facility to cover a gap at
another, subject to the same drive-time cap as drug transfers.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pandas as pd
from ortools.sat.python import cp_model

from backend.domain import OrderKind, OrderStatus, TransferOrder

from ml.optimize.constraints import SolverConfig
from ml.optimize.costs import edge_cost


def solve(
    staff_gaps: pd.DataFrame,       # facility_id, role, gap (int, staff short by)
    available_staff: pd.DataFrame,  # facility_id, role, staff_id_hash, spare (bool)
    drive: "list[list[float]]",
    facility_order: list[str],
    cfg: SolverConfig,
) -> tuple[list[TransferOrder], str | None]:
    if staff_gaps.empty or available_staff.empty:
        return [], "no staff gaps or no available staff supplied"

    idx_of = {fid: i for i, fid in enumerate(facility_order)}
    orders: list[TransferOrder] = []
    reasons: list[str] = []

    for role, gaps_g in staff_gaps.groupby("role"):
        avail_g = available_staff[(available_staff["role"] == role) & (available_staff["spare"])]
        if avail_g.empty:
            reasons.append(f"no spare {role} staff available")
            continue

        model = cp_model.CpModel()
        gaps_g = gaps_g.reset_index(drop=True)
        avail_g = avail_g.reset_index(drop=True)

        assign = {}
        edge_ok = {}
        for gi, grow in gaps_g.iterrows():
            for ai, arow in avail_g.iterrows():
                if grow["facility_id"] == arow["facility_id"]:
                    edge_ok[(gi, ai)] = False
                    continue
                s_idx, d_idx = idx_of.get(arow["facility_id"]), idx_of.get(grow["facility_id"])
                minutes = drive[s_idx][d_idx] if s_idx is not None and d_idx is not None else float("inf")
                ok = minutes <= cfg.max_drive_minutes
                edge_ok[(gi, ai)] = ok
                if ok:
                    assign[(gi, ai)] = model.NewBoolVar(f"assign_{gi}_{ai}")

        if not assign:
            reasons.append("no drive-time-feasible deputation pairing")
            continue

        # each available staff member deputed at most once
        for ai in range(len(avail_g)):
            vars_for_staff = [v for (gi, aj), v in assign.items() if aj == ai]
            if vars_for_staff:
                model.Add(sum(vars_for_staff) <= 1)
        # do not exceed the gap at any facility
        for gi, grow in gaps_g.iterrows():
            vars_for_gap = [v for (gj, ai), v in assign.items() if gj == gi]
            if vars_for_gap:
                model.Add(sum(vars_for_gap) <= int(grow["gap"]))

        total_cost = sum(
            edge_cost(drive[idx_of[avail_g.iloc[ai]["facility_id"]]][idx_of[gaps_g.iloc[gi]["facility_id"]]]) * v
            for (gi, ai), v in assign.items()
        )
        model.Maximize(sum(assign.values()) * 100000 - total_cost)  # prioritise filling gaps, then minimise travel

        solver = cp_model.CpSolver()
        status = solver.Solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            reasons.append(f"CP-SAT found no feasible deputation for role {role}")
            continue

        for (gi, ai), v in assign.items():
            if solver.Value(v):
                grow, arow = gaps_g.iloc[gi], avail_g.iloc[ai]
                s_idx, d_idx = idx_of[arow["facility_id"]], idx_of[grow["facility_id"]]
                minutes = drive[s_idx][d_idx]
                orders.append(TransferOrder(
                    order_id=str(uuid.uuid4()), kind=OrderKind.DEPUTATION,
                    from_facility_id=arow["facility_id"], to_facility_id=grow["facility_id"],
                    staff_id_hash=arow["staff_id_hash"], drive_minutes=minutes,
                    rationale=f"deputation to cover {role} staffing gap",
                    status=OrderStatus.DRAFT, created_at=datetime.now(timezone.utc), created_by="solver",
                ))

    if orders:
        return orders, None
    return [], (reasons[-1] if reasons else "no feasible deputation")
