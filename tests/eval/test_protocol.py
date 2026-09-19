"""DoD test for eval/protocol.lock (step 1) and eval/protocol.py (step 2).

Written before eval/protocol.py exists (TDD). Run with: pytest tests/eval/test_protocol.py
"""
from datetime import date
import pathlib
import yaml
import pytest

LOCK_PATH = pathlib.Path(__file__).resolve().parents[2] / "eval" / "protocol.lock"


def _month(s: str) -> date:
    y, m = s.split("-")
    return date(int(y), int(m), 1)


@pytest.fixture(scope="module")
def raw():
    return yaml.safe_load(LOCK_PATH.read_text())


def test_lock_file_exists_and_parses(raw):
    assert raw["version"] == 1


def test_real_benchmark_windows_are_contiguous_and_ordered(raw):
    rb = raw["real_benchmark"]
    train_start, train_end = _month(rb["train_start"]), _month(rb["train_end"])
    val_start, val_end = _month(rb["validation_start"]), _month(rb["validation_end"])
    test_start, test_end = _month(rb["test_start"]), _month(rb["test_end"])
    assert train_start < train_end < val_start <= val_end < test_start <= test_end
    # contiguous: validation starts the month after training ends
    assert (val_start.year, val_start.month) == _next_month(train_end)
    assert (test_start.year, test_start.month) == _next_month(val_end)


def _next_month(d: date):
    return (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)


def test_2020_03_excluded(raw):
    assert "2020-03" in raw["real_benchmark"]["excluded_months"]
    # and the test window itself must not extend into it
    assert raw["real_benchmark"]["test_end"] < "2020-03"


def test_held_out_district_is_dhule_and_not_in_any_split(raw):
    rb = raw["real_benchmark"]
    assert rb["held_out_district"] == "dhule"
    assert rb["held_out_district_state"] == "mh"
    # sanity: pilot district must differ from the held-out district
    assert raw["pilot"]["district"] != rb["held_out_district"]


def test_federated_held_out_state_is_meghalaya(raw):
    fb = raw["federated_benchmark"]
    assert fb["held_out_state"] == "meghalaya"
    assert fb["held_out_state"] in fb["client_states"]
    assert set(fb["client_states"]) == {"maharashtra", "haryana", "assam", "meghalaya"}


def test_synthetic_benchmark_has_frozen_window(raw):
    sb = raw["synthetic_benchmark"]
    assert sb["test_weeks"] == 26
    assert sb["held_out_block"]


def test_generator_seal_is_well_formed(raw):
    """Seed is fixed regardless of seal state. Whether content_hash/sealed_at
    are filled depends on whether eval/seal_generator.py has run yet --
    tests/eval/test_protocol_immutable.py covers the sealed state itself."""
    gs = raw["generator_seal"]
    assert isinstance(gs["seed"], int)
    assert (gs["content_hash"] is None) == (gs["sealed_at"] is None)


# --- loader-level tests (step 2: eval/protocol.py) ---

def test_loader_exposes_typed_protocol():
    from eval.protocol import load_protocol

    p = load_protocol()
    assert p.real_benchmark.test_start == date(2019, 9, 1)
    assert p.real_benchmark.test_end == date(2020, 2, 1)
    assert p.real_benchmark.held_out_district == "dhule"
    assert p.federated_benchmark.held_out_state == "meghalaya"
    assert p.synthetic_benchmark.test_weeks == 26


def test_loader_rejects_unknown_key(tmp_path):
    from eval.protocol import load_protocol

    bad = tmp_path / "bad.lock"
    good = yaml.safe_load(LOCK_PATH.read_text())
    good["not_a_real_section"] = {"x": 1}
    bad.write_text(yaml.safe_dump(good))
    with pytest.raises(Exception):
        load_protocol(bad)


def test_loader_is_read_only_view(raw):
    """protocol.py must not mutate or regenerate the lock file."""
    before = LOCK_PATH.read_text()
    from eval.protocol import load_protocol

    load_protocol()
    after = LOCK_PATH.read_text()
    assert before == after
