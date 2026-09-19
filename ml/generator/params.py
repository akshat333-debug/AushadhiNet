"""Generator parameters (modular-plan.md §2.8). These are the only knobs
that shape the synthetic ledger; every one of them is either an observable
seasonal/weather effect (which the forecaster is allowed to learn) or a
hidden driver (which it is not -- see data/README.md §6.2 and the module
docstring in ledger.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from backend.domain import FacilityType


@dataclass(frozen=True)
class GeneratorParams:
    seed: int

    # --- observable structure (a forecaster COULD learn these from
    # facility type, calendar month, or real weather/disease features) ---
    facility_type_weight: dict[FacilityType, float] = field(default_factory=lambda: {
        FacilityType.SC: 0.3, FacilityType.PHC: 1.0, FacilityType.CHC: 3.0,
        FacilityType.SDH: 6.0, FacilityType.DH: 10.0,
    })
    monsoon_months: tuple[int, ...] = (6, 7, 8, 9)
    monsoon_multiplier: float = 1.8  # applied to monsoon-sensitive drugs (ORS, zinc, albendazole)
    facility_heterogeneity_sigma: float = 0.35  # lognormal spread of per-facility baseline demand

    # --- hidden drivers (NOT exposed as features to ml/forecast/;
    # data/README.md §6.2 rule: the model must not be able to learn these
    # back, so nothing in ml/forecast/ may read GeneratorParams or the RNG
    # trace, only the resulting stock/dispense numbers) ---
    outbreak_shock_prob: float = 0.03      # per facility-drug-week
    outbreak_shock_multiplier: float = 3.0
    supply_delay_prob: float = 0.06        # per scheduled delivery
    supply_delay_extra_weeks: int = 2
    leakage_rate: float = 0.01             # fraction of on-hand stock lost silently each week
    reporting_noise_std: float = 0.04      # multiplicative noise on what gets *reported* as dispensed

    # --- inventory policy (order-up-to-cover, a standard PHC-style rule) ---
    lead_time_weeks: int = 2
    reorder_buffer_weeks: float = 4.0
    default_shelf_life_weeks: int = 104    # ~2 years; overridable per drug
    review_period_weeks: int = 1           # weekly review, matches FACILITY_WEEK grain
