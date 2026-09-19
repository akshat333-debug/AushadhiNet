"""Chooses SolverConfig.cover_weeks on the dev window (the 26 weeks before
the frozen synthetic test window). Never touches the test window."""
from __future__ import annotations

import sys

from eval.run_replay import run
from ml.optimize.constraints import SolverConfig

CANDIDATES = (None, 1.0, 2.0, 3.0, 4.0)


def main(candidates=CANDIDATES) -> None:
    for cover in candidates:
        r = run("dev", SolverConfig(cover_weeks=cover))
        sq, sv = r["status_quo"], r["solver"]
        print(f"cover_weeks={cover}: unmet {sv['unmet_units'] / sq['unmet_units'] - 1:+.2%}, "
              f"stock-out weeks {sv['stockout_weeks'] - sq['stockout_weeks']:+.0f}, transfers {sv['transfers']:.0f}")


if __name__ == "__main__":
    main([None if a == "legacy" else float(a) for a in sys.argv[1:]] or CANDIDATES)
