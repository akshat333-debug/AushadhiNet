"""Edge costs for the solvers (modular-plan.md §2.12). Cost units are
minutes of drive time -- no currency anywhere (architecture.md §1
convention), so a transfer, a deputation and a referral are all comparable
on the same scale.
"""
from __future__ import annotations


def edge_cost(drive_minutes: float) -> int:
    """OR-Tools min-cost-flow requires integer costs. Rounds to the
    nearest minute, floored at 1 so two facilities at effectively zero
    distance don't create a degenerate zero-cost edge."""
    return max(1, round(drive_minutes))
