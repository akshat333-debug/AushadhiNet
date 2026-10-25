"""backend/ingest/parse_text.py: typed stock reports."""
from __future__ import annotations

from backend.ingest.parse_text import from_text


def test_unknown_or_ambiguous_names_are_not_confident():
    """Regression: a fuzzy embedding match used to be written at full confidence
    ("IFA" -> rifampicin, "xyz" -> gonadotropin)."""
    from backend.ingest.gate import apply
    for body in ("IFA 20", "xyz 5"):
        result = from_text(body, "F1", "h")
        decision = apply(result.records, 0.85)
        assert decision.confirmed == [] and decision.card is not None


def test_catalogue_aliases_resolve_exactly():
    for body, expected in (("ORS 5", "ors"), ("Zinc 3", "zinc-20mg"), ("Calcium 9", "calcium-tab"), ("IFA red 4", "ifa-adult")):
        record = from_text(body, "F1", "h").records[0]
        assert record.drug_id == expected and record.confidence.overall == 1.0


def test_several_items_on_one_line_are_split():
    """Regression: "ओआरएस 50 जिंक 120" was one item, ORS 120, at full confidence."""
    def parsed(body):
        return [(r.drug_id, r.on_hand) for r in from_text(body, "F1", "h").records]
    assert parsed("ors 50 zinc 120") == [("ors", 50), ("zinc-20mg", 120)]
    assert parsed("ओआरएस 50 जिंक 120") == [("ors", 50), ("zinc-20mg", 120)]
    assert parsed("Zinc 20mg 120") == [("zinc-20mg", 120)]
    assert [q for _, q in parsed("Paracetamol 500 mg 30")] == [30]  # a unit is not a new item
