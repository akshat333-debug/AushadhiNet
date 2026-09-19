"""Splits a panel by state (modular-plan.md §2.13): the data-plane
boundary a real federation would enforce as separate GCP projects
(architecture.md §5.4) -- here, just a dict split, since no raw row ever
needs to leave this in-process boundary either.
"""
from __future__ import annotations

import pandas as pd


def by_state(panel: pd.DataFrame, state_col: str = "state_code") -> dict[str, pd.DataFrame]:
    return {state: group.reset_index(drop=True) for state, group in panel.groupby(state_col)}
