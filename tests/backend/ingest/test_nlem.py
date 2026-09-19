"""DoD test for backend/ingest/nlem.py (step 26): ≥30 misspellings, top-1
accuracy ≥0.9 against the real NLEM master + M19 item list."""
from __future__ import annotations

from backend.ingest.nlem import NLEMIndex

MISSPELLING_CASES = [
    ("paracetmol", "paracetamol"), ("paracetamol tab", "paracetamol"), ("para cetamol", "paracetamol"),
    ("ibuprofen 400", "ibuprofen"), ("ibuprofin", "ibuprofen"), ("diclofenc", "diclofenac"),
    ("zinc 20mg tab", "zinc 20 mg tablet"), ("zinc tablet 20mg", "zinc 20 mg tablet"),
    ("ors sachet new who", "ors (new who)"), ("ors new who packet", "ors (new who)"),
    ("albendazol 400", "albendazole 400 mg tablet"), ("albendazole tab", "albendazole 400 mg tablet"),
    ("gentamicin injectable", "paediatrics antibiotics ( amoxycillin and injectable gentamicin)"),
    ("paediatric antibiotics amoxycillin", "paediatrics antibiotics ( amoxycillin and injectable gentamicin)"),
    ("vitamin a syrup", "vit a syrup"), ("vit-a syrup", "vit a syrup"),
    ("calcium tab", "calcium tablets"), ("calcium tablet", "calcium tablets"),
    ("surgical gloves", "gloves"), ("mva syringe", "mva syringes"),
    ("fluconazole tablet", "tab. fluconazole"), ("flucanazole tab", "tab. fluconazole"),
    ("blood transfusion set", "blood transfusion sets"),
    ("gluteraldehyde solution", "gluteraldehyde 2%"),
    ("ifa adult tablet", "ifa tablets ( adult)"), ("ifa tablets for adults", "ifa tablets ( adult)"),
    ("ifa blue adolescent", "ifa - blue ( adolescent 10-19 yrs)"), ("ifa pink junior", "ifa- pink ( junior 6-10 yrs)"),
    ("ifa paediatric syrup", "ifa syrup (paediatric)"),
    ("rti sti syndromic kit", "rti /sti colour coded syndromic kits ( i to vii)"),
    ("diclofenac injection", "diclofenac"), ("paracetamol suppository", "paracetamol"),
]


def test_at_least_30_misspelling_cases():
    assert len(MISSPELLING_CASES) >= 30


def test_top1_accuracy_at_least_90_percent():
    index = NLEMIndex()
    correct = 0
    misses = []
    for query, expected_alias in MISSPELLING_CASES:
        expected_id = index.alias_to_id[expected_alias]  # fails loudly if the fixture alias itself is wrong
        result = index.match(query, k=1)
        if result and result[0].drug_id == expected_id:
            correct += 1
        else:
            misses.append((query, result[0].drug_id if result else None, expected_id))
    accuracy = correct / len(MISSPELLING_CASES)
    assert accuracy >= 0.9, f"top-1 accuracy {accuracy:.2%} below 0.9; misses: {misses}"


def test_exact_alias_short_circuits_to_score_1():
    index = NLEMIndex()
    result = index.match("ORS (New WHO)", k=1)
    assert result[0].score == 1.0


def test_match_returns_at_most_k_results():
    index = NLEMIndex()
    result = index.match("paracetamol", k=2)
    assert len(result) <= 2


def test_case_insensitive_exact_match():
    index = NLEMIndex()
    result = index.match("ors (new who)", k=1)
    assert result[0].score == 1.0
