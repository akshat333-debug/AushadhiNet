"""Weekly use read from a facility's own stock counts: the one estimator the live app
(backend/runtime.py) and the end-to-end replay (eval/replay_sim.py) share.

Between two counts a day or more apart, use = first count + units that arrived - units that
left - second count. Counts closer together than a day keep the older count as the anchor, so
frequent reporting still measures. A second count of zero is censored: the shelf was empty for
part of the interval, so true demand is at least what was used; it can raise the estimate,
never lower it. Otherwise each new reading is averaged with the previous one (half weight
each), so one odd count does not swing next week's demand.
"""
from __future__ import annotations

from dataclasses import dataclass, field

MIN_DAYS = 1.0


@dataclass
class UseEstimator:
    anchors: dict = field(default_factory=dict)   # key -> (day, on_hand)
    rates: dict = field(default_factory=dict)     # key -> units per week

    def anchor(self, key):
        return self.anchors.get(key)

    def observe(self, key, day: float, on_hand: float, net_in: float = 0.0) -> bool:
        """`day` in days (any origin); `net_in` = units received minus units sent since the
        anchor's day. Returns True when the estimate changed."""
        anchor = self.anchors.get(key)
        if anchor is None:
            self.anchors[key] = (day, on_hand)
            return False
        days = day - anchor[0]
        if days < MIN_DAYS:
            return False
        self.anchors[key] = (day, on_hand)
        used = anchor[1] + net_in - on_hand
        if used < 0:  # an unrecorded delivery, or a miscount: no reading
            return False
        rate = 7 * used / days
        if on_hand <= 0:
            if rate <= self.rates.get(key, 0.0):
                return False
            self.rates[key] = rate  # a lower bound: true use was at least this
            return True
        self.rates[key] = (rate + self.rates[key]) / 2 if key in self.rates else rate
        return True
