"""DoD test for eval/run_replay.py (step 24, AC6)."""
from __future__ import annotations

from eval.run_replay import run


def test_replay_reports_both_policies():
    result = run()
    assert "baseline" in result and "solver_assisted" in result
    assert "stockout_weeks" in result["baseline"]
    assert "expired_units" in result["baseline"]


def test_solver_assisted_does_not_report_more_stockouts_than_baseline():
    """The solver-assisted policy resolves shortfalls it can cover with
    same-district surplus, so it can only match or beat the do-nothing
    baseline, never do worse."""
    result = run()
    assert result["solver_assisted"]["stockout_weeks"] <= result["baseline"]["stockout_weeks"]
