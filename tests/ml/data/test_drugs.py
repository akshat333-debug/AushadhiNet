"""DoD test for ml/data/drugs.py (step 8)."""
from __future__ import annotations

from ml.data.drugs import M19_ITEMS, load_nlem


def test_at_least_300_drugs():
    drugs = load_nlem()
    assert len(drugs) >= 300


def test_every_m19_item_present_as_an_alias():
    drugs = load_nlem()
    all_aliases = {alias for d in drugs for alias in d.aliases}
    missing = [item for item in M19_ITEMS if item not in all_aliases]
    assert not missing, f"M19 items missing from NLEM master: {missing}"


def test_drug_ids_are_unique():
    drugs = load_nlem()
    ids = [d.drug_id for d in drugs]
    assert len(ids) == len(set(ids))


def test_nlem_levels_are_valid():
    drugs = load_nlem()
    assert all(d.nlem_level in ("P", "S", "T") for d in drugs)


def test_known_essential_drugs_present():
    drugs = load_nlem()
    names = {d.name.lower() for d in drugs}
    for expected in ("paracetamol", "ibuprofen", "diclofenac"):
        assert any(expected in n for n in names), f"{expected} not found in parsed NLEM"
