"""Train/validation-only backtest runner (modular-plan.md §2.10, step 15).

This is where "the forecaster never sees the test window during
development" is enforced in code, not just in the plan: `run_backtest`
refuses outright if asked to touch the test split. Only eval/run_final.py
(step 21) is allowed to score the frozen test window, and it does so
exactly once per model per run, appended to reports/runs.jsonl.
"""
from __future__ import annotations

import pandas as pd

from backend.domain import Grain

from eval.protocol import Protocol, load_protocol
from eval.splits import Split, for_grain


class TestWindowAccessError(RuntimeError):
    """Raised when a backtest run asks for the test split. Use
    eval/run_final.py for that, deliberately and exactly once."""

    __test__ = False  # tell pytest this is not a test class despite the name


def backtest_data(
    panel: pd.DataFrame,
    grain: Grain,
    protocol: Protocol | None = None,
    include: tuple[str, ...] = ("train", "val"),
) -> dict[str, pd.DataFrame]:
    """Returns {"train": df, "val": df} (or a subset of `include`).
    Raises TestWindowAccessError if "test" is requested here."""
    if "test" in include:
        raise TestWindowAccessError(
            "run_backtest.backtest_data() refuses to return the test split. "
            "Use eval/run_final.py to score the frozen test window."
        )
    protocol = protocol or load_protocol()
    panel_max_date = pd.to_datetime(panel["month" if grain == Grain.DISTRICT_MONTH else "week"]).max().date()
    split = for_grain(grain, protocol, panel_max_date=panel_max_date if grain == Grain.FACILITY_WEEK else None)

    out: dict[str, pd.DataFrame] = {}
    if "train" in include:
        out["train"] = panel[split.train_mask(panel)].reset_index(drop=True)
    if "val" in include:
        out["val"] = panel[split.val_mask(panel)].reset_index(drop=True)
    return out
