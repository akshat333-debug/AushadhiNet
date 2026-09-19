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
