"""ID conventions (modular-plan.md §1)."""
from __future__ import annotations

import re

_STATE_CODES = {"maharashtra": "MH", "haryana": "HR", "assam": "AS", "meghalaya": "ML"}

_SLUG_RE = re.compile(r"[^a-z0-9]+")

# Known spelling variants across government data sources for the same
# district (found while joining HMIS district names against the facility
# directory -- data/README.md). Add entries here as more mismatches turn up;
# this is the one place district-name normalisation happens.
_DISTRICT_ALIASES = {
    "ahmadnagar": "ahmednagar",
}


def slugify(text: str) -> str:
    return _SLUG_RE.sub("-", text.strip().lower()).strip("-")


def district_id(state_name: str, district_name: str) -> str:
    """e.g. district_id("Maharashtra", "Nashik") -> "mh/nashik"."""
    code = _STATE_CODES.get(state_name.strip().lower(), slugify(state_name)[:2])
    slug = _DISTRICT_ALIASES.get(slugify(district_name), slugify(district_name))
    return f"{code.lower()}/{slug}"


def facility_id(state_name: str, sequence: int | str) -> str:
    """e.g. facility_id("Maharashtra", 1234) -> "MH-1234" (state-prefixed)."""
    code = _STATE_CODES.get(state_name.strip().lower(), slugify(state_name)[:2].upper())
    return f"{code}-{int(sequence):07d}" if isinstance(sequence, int) or str(sequence).isdigit() else f"{code}-{sequence}"


def drug_id(name: str, strength: str | None = None) -> str:
    """e.g. drug_id("ORS", "New WHO") -> "ors-new-who"."""
    parts = [name] + ([strength] if strength else [])
    return slugify(" ".join(parts))
