"""Solver-wide constraints (modular-plan.md §2.12): retention buffer, cold
chain, drive-time cap. FEFO batch ordering lives in transfers.py itself
(it's about *which units* move, not *whether* a transfer is allowed).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SolverConfig:
    buffer_floor: float = 0.0        # minimum stock a source must retain after transferring
    max_drive_minutes: float = 120.0  # hard cap: no transfer beyond this drive time
    respect_cold_chain: bool = True   # a cold-chain drug may only move between cold-chain-capable facilities
    # Weeks of demand both sides plan for: a donor keeps cover_weeks x p90 for itself and a
    # recipient is topped up to cover_weeks x p50. None = legacy one-week stock-out-probability rule.
    # 2.0 chosen on the replay dev window by AC6's metric, stock-out weeks (eval/tune_replay.py).
    cover_weeks: float | None = 2.0


def edge_feasible(
    drive_minutes: float,
    drug_cold_chain: bool,
    source_has_cold_chain: bool,
    dest_has_cold_chain: bool,
    cfg: SolverConfig,
) -> tuple[bool, str | None]:
    """Returns (feasible, reason_if_not)."""
    if drive_minutes > cfg.max_drive_minutes:
        return False, f"drive time {drive_minutes:.0f}min exceeds cap {cfg.max_drive_minutes:.0f}min"
    if cfg.respect_cold_chain and drug_cold_chain and not (source_has_cold_chain and dest_has_cold_chain):
        return False, "cold-chain drug requires cold-chain capability at both ends"
    return True, None


def available_after_buffer(on_hand: float, cfg: SolverConfig) -> float:
    """Surplus quantity actually offerable for transfer, after retaining
    the buffer floor. Never negative."""
    return max(0.0, on_hand - cfg.buffer_floor)
