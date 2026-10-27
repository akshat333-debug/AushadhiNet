"""The judge's three cases for demand read from stock counts."""
from ml.forecast.reported_use import UseEstimator


def test_units_sent_away_are_not_use():
    e = UseEstimator()
    e.observe("k", 0, 100)
    e.observe("k", 1, 20, net_in=-80)  # 80 dispatched, nobody treated
    assert e.rates["k"] == 0


def test_twice_daily_counts_still_measure_against_a_day_old_anchor():
    e = UseEstimator()
    for half_day, on_hand in enumerate((100, 90, 80, 70, 60)):  # 40 used over two days
        e.observe("k", half_day / 2, on_hand)
    assert e.rates["k"] == 7 * 20 / 1  # each full day used 20; the two readings agree


def test_an_empty_shelf_never_lowers_the_estimate():
    e = UseEstimator()
    e.observe("k", 0, 70)
    e.observe("k", 1, 10)    # 60 a day = 420 a week
    e.observe("k", 2, 0)     # stocked out: at least 70 a week, says nothing about the rest
    e.observe("k", 3, 0)     # empty both days: 0 used, censored
    assert e.rates["k"] == 420


def test_a_facility_new_to_the_ledger_is_forecast_from_its_own_use():
    import datetime
    import pandas as pd
    from ml.forecast.service import latest_forecasts
    empty = pd.DataFrame(columns=["facility_id", "drug_id", "week", "dispensed", "on_hand_close"])
    f = latest_forecasts(["NEW-1"], ["ors"], panel=empty, on_hand={("NEW-1", "ors"): 10.0},
                         recent_use={("NEW-1", "ors"): (70.0, datetime.date(2026, 10, 27))})
    assert len(f) == 1 and f[0].model == "reported_use" and f[0].p50 == 70 and f[0].p10 < 70 < f[0].p90
    assert f[0].stockout_prob > 0.5  # 10 on hand against 70 a week
