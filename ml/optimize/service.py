"""`propose(district_id) -> list[TransferOrder]` (modular-plan.md §2.12):
runs all three solvers (drug transfer, deputation, referral) for one
district's facility cluster and returns every proposal as a draft order.
This is the one seam backend/agent's `propose_order` tool calls into
(modular-plan.md §5 gap #5) -- the agent never touches solver internals.
"""
from __future__ import annotations

import pandas as pd

from backend.domain import Facility, TransferOrder

from ml.data.graph import drive_matrix
from ml.forecast.service import latest_forecasts
from ml.optimize.constraints import SolverConfig
from ml.optimize import deputation, referral, transfers


def _surplus_deficit_from_forecasts(forecasts, stock_by_facility_drug: dict, cold_chain_by_drug: dict, cold_chain_by_facility: dict, cover_weeks: float | None = None):
    surplus_rows, deficit_rows = [], []
    for f in forecasts:
        on_hand = stock_by_facility_drug.get((f.entity_id, f.drug_id), 0.0)
        row_common = {
            "facility_id": f.entity_id, "drug_id": f.drug_id,
            "drug_cold_chain": cold_chain_by_drug.get(f.drug_id, False),
            "has_cold_chain": cold_chain_by_facility.get(f.entity_id, False),
        }
        if cover_weeks is not None:
            need = f.p50 * cover_weeks - on_hand
            spare = on_hand - f.p90 * cover_weeks
            if need >= 1:
                deficit_rows.append({**row_common, "needed_qty": round(need)})
            elif spare >= 1:
                surplus_rows.append({**row_common, "on_hand": spare, "batches": []})
            continue
        if f.stockout_prob >= 0.5:
            deficit_rows.append({**row_common, "needed_qty": max(1, round(f.p50 - on_hand))})
        elif f.stockout_prob <= 0.1 and on_hand > f.p90:
            surplus_rows.append({**row_common, "on_hand": on_hand, "batches": []})
    return pd.DataFrame(surplus_rows), pd.DataFrame(deficit_rows)


def propose(
    facilities: list[Facility],
    drug_ids: list[str],
    cold_chain_by_drug: dict[str, bool],
    stock_by_facility_drug: dict[tuple[str, str], float],
    cfg: SolverConfig | None = None,
    panel: pd.DataFrame | None = None,
) -> list[TransferOrder]:
    """Forecast-driven drug transfer proposals for a facility cluster
    (typically one district). Deputation and referral need staffing/bed
    inputs this function does not itself compute (those come from
    backend/ingest live data, not the forecast panel), so callers that
    want those too should call ml.optimize.deputation.solve /
    ml.optimize.referral.solve directly with real inputs -- this function
    covers the drug-transfer path end to end, which is what forecasts
    alone can drive."""
    cfg = cfg or SolverConfig()
    facility_ids = [f.facility_id for f in facilities]
    cold_chain_by_facility = {f.facility_id: f.has_cold_chain for f in facilities}

    forecasts = latest_forecasts(facility_ids, drug_ids, panel=panel, on_hand=stock_by_facility_drug)
    surplus, deficit = _surplus_deficit_from_forecasts(
        forecasts, stock_by_facility_drug, cold_chain_by_drug, cold_chain_by_facility, cfg.cover_weeks,
    )
    if surplus.empty or deficit.empty:
        return []

    drive = drive_matrix(facilities).tolist()
    orders, _reason = transfers.solve(surplus, deficit, drive, facility_ids, cfg)
    return orders
