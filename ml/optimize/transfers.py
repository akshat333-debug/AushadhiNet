"""Min-cost-flow drug redistribution (modular-plan.md §2.12), one drug at
a time (drugs are not fungible with each other, so the problem decomposes
cleanly). Uses OR-Tools SimpleMinCostFlow.

Gap resolved conservatively: the plan's public interface is
`solve(surplus, deficit, drive, cfg) -> list[TransferOrder]`. Building a
concrete order needs to look up a facility's position in `drive` by its
id, so `solve()` also takes `facility_order` (the id list `drive`'s rows/
columns are indexed by) -- a small, necessary addition, not a redesign.
Returns `(orders, reason)`: `reason` is None on success, or a human-
readable string when no feasible transfer exists at all (AC6: an
infeasible instance returns `[]` and a reason, never a partial illegal
plan).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pandas as pd
from ortools.graph.python import min_cost_flow as mcf_module

from backend.domain import BatchLine, OrderKind, OrderStatus, TransferOrder

from ml.optimize.constraints import SolverConfig, available_after_buffer, edge_feasible
from ml.optimize.costs import edge_cost


def _fefo_batches(batches: list[dict], quantity: float) -> list[BatchLine]:
    """Picks batches earliest-expiring first until `quantity` is covered."""
    ordered = sorted(batches, key=lambda b: b["expiry"])
    picked: list[BatchLine] = []
    remaining = quantity
    for b in ordered:
        if remaining <= 1e-9:
            break
        take = min(b["qty"], remaining)
        if take > 0:
            picked.append(BatchLine(batch_no=b["batch_no"], quantity=int(round(take)), expiry=b["expiry"]))
            remaining -= take
    return picked


def _feasible_edges_for_drug(surplus_g, deficit_g, drive, idx_of, cfg):
    """Returns (edges, infeasible_reasons) for one drug's surplus/deficit rows."""
    edges = []
    infeasible_reasons = []
    for si, srow in surplus_g.reset_index().iterrows():
        for di, drow in deficit_g.reset_index().iterrows():
            if srow["facility_id"] == drow["facility_id"]:
                continue
            s_idx, d_idx = idx_of.get(srow["facility_id"]), idx_of.get(drow["facility_id"])
            if s_idx is None or d_idx is None:
                continue
            minutes = drive[s_idx][d_idx]
            feasible, edge_reason = edge_feasible(
                minutes, bool(srow["drug_cold_chain"]), bool(srow["has_cold_chain"]),
                bool(drow["has_cold_chain"]), cfg,
            )
            if feasible:
                edges.append((si, di, edge_cost(minutes), minutes))
            else:
                infeasible_reasons.append(edge_reason)
    return edges, infeasible_reasons


def solve(
    surplus: pd.DataFrame,
    deficit: pd.DataFrame,
    drive: "list[list[float]]",
    facility_order: list[str],
    cfg: SolverConfig,
) -> tuple[list[TransferOrder], str | None]:
    """surplus columns: facility_id, drug_id, on_hand, drug_cold_chain,
    has_cold_chain, batches (list of {batch_no, qty, expiry}).
    deficit columns: facility_id, drug_id, needed_qty, drug_cold_chain,
    has_cold_chain.
    """
    if surplus.empty or deficit.empty:
        return [], "no surplus or no deficit rows supplied"

    idx_of = {fid: i for i, fid in enumerate(facility_order)}
    orders: list[TransferOrder] = []
    all_infeasible_reasons: list[str] = []

    for drug_id, surplus_g in surplus.groupby("drug_id"):
        deficit_g = deficit[deficit["drug_id"] == drug_id]
        if deficit_g.empty:
            continue

        surplus_g = surplus_g.copy()
        surplus_g["offerable"] = surplus_g["on_hand"].apply(lambda q: available_after_buffer(q, cfg))
        surplus_g = surplus_g[surplus_g["offerable"] > 0]
        if surplus_g.empty:
            continue

        edges, infeasible_reasons = _feasible_edges_for_drug(surplus_g, deficit_g, drive, idx_of, cfg)
        all_infeasible_reasons.extend(infeasible_reasons)
        if not edges:
            continue

        smcf = mcf_module.SimpleMinCostFlow()
        n_surplus, n_deficit = len(surplus_g), len(deficit_g)
        SOURCE, SINK = n_surplus + n_deficit, n_surplus + n_deficit + 1

        for si, val in enumerate(surplus_g["offerable"]):
            smcf.add_arc_with_capacity_and_unit_cost(SOURCE, si, int(round(val)), 0)
        for di, val in enumerate(deficit_g["needed_qty"]):
            smcf.add_arc_with_capacity_and_unit_cost(n_surplus + di, SINK, int(round(val)), 0)
        arc_lookup = {}
        for si, di, cost, minutes in edges:
            cap = min(int(round(surplus_g["offerable"].iloc[si])), int(round(deficit_g["needed_qty"].iloc[di])))
            if cap <= 0:
                continue
            arc_idx = smcf.add_arc_with_capacity_and_unit_cost(si, n_surplus + di, cap, cost)
            arc_lookup[arc_idx] = (si, di, minutes)

        total_supply = int(round(surplus_g["offerable"].sum()))
        total_demand = int(round(deficit_g["needed_qty"].sum()))
        flow_target = min(total_supply, total_demand)
        smcf.set_node_supply(SOURCE, flow_target)
        smcf.set_node_supply(SINK, -flow_target)

        status = smcf.solve_max_flow_with_min_cost()
        if status != smcf.OPTIMAL:
            continue

        for arc_idx, (si, di, minutes) in arc_lookup.items():
            qty = smcf.flow(arc_idx)
            if qty <= 0:
                continue
            srow, drow = surplus_g.iloc[si], deficit_g.iloc[di]
            batches = _fefo_batches(srow.get("batches", []) or [], qty)
            if not batches:
                batches = [BatchLine(batch_no=f"{drug_id}-unbatched", quantity=int(qty))]
            orders.append(TransferOrder(
                order_id=str(uuid.uuid4()), kind=OrderKind.DRUG_TRANSFER,
                from_facility_id=srow["facility_id"], to_facility_id=drow["facility_id"],
                drug_id=drug_id, quantity=int(sum(b.quantity for b in batches)),
                batches=batches, drive_minutes=minutes,
                rationale=f"stock-out risk transfer of {drug_id}",
                status=OrderStatus.DRAFT, created_at=datetime.now(timezone.utc), created_by="solver",
            ))

    if orders:
        return orders, None
    if all_infeasible_reasons:
        return [], all_infeasible_reasons[-1]
    return [], "no feasible edge under current constraints"
